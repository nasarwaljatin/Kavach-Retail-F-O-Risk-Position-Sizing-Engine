"""
Paper trading broker adapter.

PaperBrokerAdapter wraps a real AngelOneBroker:
  - READ operations (positions, margins, quotes, order book) → delegate to
    the real broker, giving realistic live data for risk calculations.
  - WRITE operations (place_order, cancel_order, square_off_all) → write to
    the paper_orders DB table only.  No real order is ever sent.

This satisfies the acceptance criteria: run a full trading day with
PAPER_MODE=True and verify Angel One's own order book stays empty.
"""

import logging
import random
from datetime import datetime
from typing import List, Dict

from sqlalchemy.orm import Session

from app.broker.base import BaseBroker, Position, MarginData, OrderParams, OrderResult
from app.db.session import SessionLocal
from app.models.paper_order import PaperOrder

logger = logging.getLogger("kavach.broker.paper")


class PaperBrokerAdapter(BaseBroker):
    """
    Wraps any BaseBroker implementation and intercepts order writes.
    Nothing downstream needs to know whether it's talking to this adapter
    or to a real broker — that's the contract of BaseBroker.
    """

    def __init__(self, real_broker: BaseBroker) -> None:
        self._broker = real_broker

    # ------------------------------------------------------------------
    # Pass-through reads — use live data for realistic risk calculations
    # ------------------------------------------------------------------

    def authenticate(self) -> bool:
        return self._broker.authenticate()

    def get_positions(self) -> List[Position]:
        return self._broker.get_positions()

    def get_margins(self) -> MarginData:
        return self._broker.get_margins()

    def get_quote(self, exchange: str, symbol: str, token: str) -> Dict:
        return self._broker.get_quote(exchange, symbol, token)

    def get_order_book(self) -> List[Dict]:
        """
        Returns ONLY paper orders for this session — the real broker's order
        book is intentionally not surfaced so callers can verify no real orders
        leaked.
        """
        db: Session = SessionLocal()
        try:
            rows = db.query(PaperOrder).order_by(PaperOrder.ts.desc()).limit(200).all()
            return [
                {
                    "orderid": str(r.id),
                    "tradingsymbol": r.symbol,
                    "symboltoken": r.symbol_token or "",
                    "transactiontype": r.transaction_type,
                    "exchange": r.exchange,
                    "ordertype": r.order_type,
                    "producttype": r.product_type,
                    "status": r.status,
                    "quantity": str(r.quantity),
                    "price": str(r.price),
                    "averageprice": str(r.fill_price or r.price),
                    "updatetime": r.ts.isoformat() + "Z",
                }
                for r in rows
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Intercepted writes — DB only, no real orders
    # ------------------------------------------------------------------

    def place_order(self, params: OrderParams) -> OrderResult:
        """Log order to paper_orders table. Never calls real broker."""
        # Attempt to get a realistic fill price from live quote
        fill_price = params.price
        if fill_price == 0.0:
            quote = self._broker.get_quote(params.exchange, params.symbol, params.symbol_token or "")
            fill_price = float(quote.get("ltp", 0.0))

        synthetic_id = f"PAPER_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}"

        db: Session = SessionLocal()
        try:
            record = PaperOrder(
                symbol=params.symbol,
                exchange=params.exchange,
                transaction_type=params.transaction_type,
                quantity=params.quantity,
                price=params.price,
                order_type=params.order_type,
                product_type=params.product_type,
                symbol_token=params.symbol_token,
                status="PAPER_COMPLETE",
                fill_price=fill_price,
                notes=f"paper_id={synthetic_id}",
            )
            db.add(record)
            db.commit()
            logger.info(
                "PAPER ORDER: %s %s %d qty @ %.2f (id=%s)",
                params.transaction_type,
                params.symbol,
                params.quantity,
                fill_price,
                synthetic_id,
            )
        except Exception as exc:
            logger.error("Failed to write paper order to DB: %s", exc)
            db.rollback()
        finally:
            db.close()

        return OrderResult(
            order_id=synthetic_id,
            status="SUCCESS",
            message="Paper order logged (no real order placed).",
        )

    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> OrderResult:
        """Mark a paper order as cancelled in DB."""
        # order_id for paper orders is the DB row id (as string) or synthetic id
        db: Session = SessionLocal()
        try:
            # Try matching by notes field (synthetic_id) or id
            row = db.query(PaperOrder).filter(
                PaperOrder.notes.contains(order_id)
            ).first()
            if row:
                row.status = "PAPER_CANCELLED"
                db.commit()
                return OrderResult(order_id=order_id, status="SUCCESS", message="Paper order cancelled.")
            return OrderResult(order_id=order_id, status="FAILED", message="Paper order not found.")
        finally:
            db.close()

    def square_off_all(self) -> List[OrderResult]:
        """
        Place paper sell/buy orders for every open position.
        All writes go to paper_orders only — real broker order book stays untouched.
        """
        logger.warning("PAPER square_off_all triggered — logging simulated exit orders.")
        positions = self.get_positions()
        results: List[OrderResult] = []

        for pos in positions:
            if pos.qty == 0:
                continue
            tx_type = "SELL" if pos.qty > 0 else "BUY"
            params = OrderParams(
                symbol=pos.symbol,
                exchange=pos.exchange,
                transaction_type=tx_type,
                order_type="MARKET",
                product_type=pos.product_type,
                quantity=abs(pos.qty),
                symbol_token=pos.symbol_token,
            )
            results.append(self.place_order(params))

        logger.info("PAPER square_off_all: %d exit orders logged.", len(results))
        return results
