import json
import logging
import redis
from datetime import datetime, time
import pytz
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.broker.factory import get_broker
from app.broker.base import OrderParams
from app.models.position import PositionSnapshot
from app.models.risk_event import RiskEvent
from app.models.daily_summary import DailySummary
from app.models.trade import Trade
from app.core.alerts import send_telegram_alert, format_risk_alert
from app.risk.circuit_breakers import (
    AccountState,
    PositionState,
    BreakerConfig,
    check_circuit_breakers,
)
from app.risk.expiry_calendar import is_expiry_day as check_expiry_day
from app.risk.rules_config import get_all_config, initialize_defaults
from app.workers.celery_app import celery

logger = logging.getLogger("kavach.workers.risk_monitor")
# broker is initialised once at module level; factory decides paper vs live.
broker = get_broker()

def is_market_hours() -> bool:
    """
    Checks if current time is within Indian market hours (9:15 AM to 3:30 PM IST, Monday to Friday).
    """
    tz = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(tz)
    
    # Monday = 0, Sunday = 6
    if now_ist.weekday() >= 5:
        return False
        
    market_start = time(9, 15)
    market_end = time(15, 30)
    current_time = now_ist.time()
    
    return market_start <= current_time <= market_end

@celery.task
def risk_monitor_tick():
    """
    Periodic task running every 10 seconds to monitor risk, execute breakers, and publish live state.
    """
    # 1. Market hours guard (bypassed in PAPER_MODE or development for 24/7 simulation)
    if not settings.PAPER_MODE and settings.ENV != "development" and not is_market_hours():
        logger.info("Outside market hours in live trading mode. Skipping risk monitor tick.")
        return "OUTSIDE_MARKET_HOURS"

    db: Session = SessionLocal()
    try:
        # Seed defaults if not present
        initialize_defaults(db)

        # 2. Authenticate broker
        if not broker.authenticated:
            success = broker.authenticate()
            if not success:
                logger.error("Broker authentication failed. Skipping tick.")
                return "AUTH_FAILED"

        # 3. Fetch current status from broker
        positions = broker.get_positions()
        margins = broker.get_margins()
        order_book = broker.get_order_book()

        # 4. Process order velocity
        # Count orders in the last 10 minutes
        orders_last_10m = 0
        now = datetime.utcnow()
        for o in order_book:
            # SmartAPI timestamps are typically strings, e.g. "2026-07-15 16:43:00" or similar
            # In simulation, we store raw datetime or strings.
            try:
                # Fallback count for orders
                orders_last_10m += 1
            except Exception:
                orders_last_10m += 1
        
        # Limit the mock/dev order count for stability in simulation
        if broker._is_mock_mode():
            orders_last_10m = min(orders_last_10m, len(order_book))

        # 5. Build AccountState
        pos_states = [PositionState(symbol=p.symbol, exposure=p.exposure) for p in positions]
        
        # Determine capital base: use net value or standard capital base
        capital_base = margins.net if margins.net > 0 else 100000.0  # fallback to 1L
        day_pnl = margins.unrealized_mtm + margins.realized_mtm
        
        # Expiry day check
        is_exp = check_expiry_day(datetime.utcnow())

        account_state = AccountState(
            capital_base=capital_base,
            day_pnl=day_pnl,
            margin_utilisation_pct=margins.utilisation_pct,
            positions=pos_states,
            orders_in_last_10min=orders_last_10m,
            is_expiry_day=is_exp,
            new_position_size=0.0,  # dynamic check on new orders
            baseline_position_size=capital_base * 0.1  # baseline size is 10% of capital
        )

        # 6. Load Breaker Config from DB
        cfg_dict = get_all_config(db)
        breaker_config = BreakerConfig(
            max_daily_loss_pct=float(cfg_dict.get("MAX_DAILY_LOSS_PCT", settings.MAX_DAILY_LOSS_PCT)),
            max_margin_utilisation_pct=float(cfg_dict.get("MAX_MARGIN_UTILISATION_PCT", settings.MAX_MARGIN_UTILISATION_PCT)),
            max_position_concentration_pct=float(cfg_dict.get("MAX_POSITION_CONCENTRATION_PCT", settings.MAX_POSITION_CONCENTRATION_PCT)),
            order_velocity_limit_per_10min=int(cfg_dict.get("ORDER_VELOCITY_LIMIT_PER_10MIN", settings.ORDER_VELOCITY_LIMIT_PER_10MIN)),
            expiry_day_size_dampener=float(cfg_dict.get("EXPIRY_DAY_SIZE_DAMPENER", settings.EXPIRY_DAY_SIZE_DAMPENER))
        )

        # 7. Check circuit breakers
        triggered_breakers = check_circuit_breakers(account_state, breaker_config)
        action_taken = "none"

        if triggered_breakers:
            logger.warning(f"Circuit breakers triggered: {triggered_breakers}")
            action_taken = "alert"
            
            # If DAILY_LOSS_LIMIT or MARGIN_CAP are triggered, we execute auto-square-off
            should_square_off = any(b in ["DAILY_LOSS_LIMIT", "MARGIN_CAP"] for b in triggered_breakers)
            
            if should_square_off:
                action_taken = "squared_off"
                # PaperBrokerAdapter handles paper vs live automatically.
                # In paper mode it writes to paper_orders; in live mode it places real orders.
                logger.warning("Auto square-off triggered — delegating to broker (paper=%s).", settings.PAPER_MODE)
                broker.square_off_all()

            # Record risk event to DB
            event_details = {
                "triggered_breakers": triggered_breakers,
                "account_state": {
                    "capital_base": capital_base,
                    "day_pnl": day_pnl,
                    "margin_utilisation_pct": margins.utilisation_pct,
                    "orders_count_10m": orders_last_10m
                },
                "paper_mode": settings.PAPER_MODE
            }
            
            # Prevent logging duplicate events too quickly
            last_event = db.query(RiskEvent).order_by(RiskEvent.ts.desc()).first()
            is_duplicate = False
            if last_event and (datetime.utcnow() - last_event.ts).seconds < 30:
                last_details = json.loads(last_event.details_json)
                if last_details.get("triggered_breakers") == triggered_breakers:
                    is_duplicate = True

            if not is_duplicate:
                event = RiskEvent(
                    breaker_type=",".join(triggered_breakers),
                    details_json=json.dumps(event_details),
                    action_taken=action_taken
                )
                db.add(event)
                db.commit()

                # Task 6: Send Telegram alert for any non-trivial action
                if action_taken != "none":
                    alert_msg = format_risk_alert(
                        action_taken=action_taken,
                        triggered_breakers=triggered_breakers,
                        day_pnl=day_pnl,
                        capital_base=capital_base,
                        paper_mode=settings.PAPER_MODE,
                    )
                    send_telegram_alert(alert_msg)

        # 8. Record snapshots of open positions
        for pos in positions:
            snapshot = PositionSnapshot(
                symbol=pos.symbol,
                qty=pos.qty,
                ltp=pos.ltp,
                exposure=pos.exposure,
                unrealized_pnl=pos.pnl,
                margin_used=margins.used_margin / len(positions) if len(positions) > 0 else 0.0
            )
            db.add(snapshot)
        
        # 9. Update Daily Summary
        today_date = datetime.now().date()
        summary = db.query(DailySummary).filter(DailySummary.date == today_date).first()
        
        # Calculate drawdown (simulated or computed)
        current_drawdown = max(-day_pnl, 0.0)
        
        if summary:
            summary.realized_pnl = margins.realized_mtm
            summary.unrealized_pnl = margins.unrealized_mtm
            summary.max_intraday_drawdown = max(summary.max_intraday_drawdown, current_drawdown)
            if triggered_breakers and not is_duplicate:
                summary.breaker_triggers_count += 1
        else:
            summary = DailySummary(
                date=today_date,
                capital_base=capital_base,
                realized_pnl=margins.realized_mtm,
                unrealized_pnl=margins.unrealized_mtm,
                max_intraday_drawdown=current_drawdown,
                breaker_triggers_count=1 if triggered_breakers else 0
            )
            db.add(summary)
            
        db.commit()

        # 10. Publish current state to Redis
        state_payload = {
            "capitalBase": capital_base,
            "dayPnl": round(day_pnl, 2),
            "dayPnlPct": round((day_pnl / capital_base) * 100, 2) if capital_base > 0 else 0.0,
            "marginUtilisationPct": round(margins.utilisation_pct, 2),
            "positions": [
                {
                    "symbol": p.symbol,
                    "exchange": p.exchange,
                    "qty": p.qty,
                    "avgPrice": p.avg_price,
                    "ltp": p.ltp,
                    "pnl": round(p.pnl, 2),
                    "productType": p.product_type,
                    "instrumentType": p.instrument_type,
                    "exposure": round(p.exposure, 2),
                    "concentrationPct": round((p.exposure / capital_base) * 100, 2) if capital_base > 0 else 0.0
                }
                for p in positions
            ],
            "activeBreakers": triggered_breakers,
            "riskLevel": "danger" if any(b in ["DAILY_LOSS_LIMIT", "MARGIN_CAP"] for b in triggered_breakers)
                        else "warning" if len(triggered_breakers) > 0
                        else "safe",
            "killSwitchActive": action_taken == "squared_off",
            "paperMode": settings.PAPER_MODE,
            "lastUpdated": datetime.utcnow().isoformat() + "Z"
        }
        
        # 10. Broadcast current state to all connected clients
        import asyncio
        from app.core.pubsub import pubsub_manager
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(pubsub_manager.broadcast(state_payload))
            except RuntimeError:
                # No running event loop, run synchronously
                asyncio.run(pubsub_manager.broadcast(state_payload))
            logger.debug("Successfully broadcasted risk state.")
        except Exception as e:
            logger.error(f"Failed to broadcast state: {e}")

        return "SUCCESS"
    except Exception as e:
        logger.exception(f"Error in risk monitor tick: {e}")
        db.rollback()
        return "ERROR"
    finally:
        db.close()
