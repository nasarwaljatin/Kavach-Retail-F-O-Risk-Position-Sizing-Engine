from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.session import get_db
from app.models.daily_summary import DailySummary
from app.models.risk_event import RiskEvent

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/summary")
def get_daily_summaries(days: int = 30, db: Session = Depends(get_db)):
    """Retrieve daily summary rows for the dashboard charts."""
    summaries = db.query(DailySummary).order_by(DailySummary.date.desc()).limit(days).all()
    # Reverse so it's chronological in charts
    summaries.reverse()
    
    return [
        {
            "date": s.date.strftime("%Y-%m-%d"),
            "capitalBase": s.capital_base,
            "realizedPnl": s.realized_pnl,
            "unrealizedPnl": s.unrealized_pnl,
            "maxDrawdown": s.max_intraday_drawdown,
            "breakerTriggers": s.breaker_triggers_count
        }
        for s in summaries
    ]

@router.get("/metrics")
def get_portfolio_metrics(db: Session = Depends(get_db)):
    """Compute overall risk engine statistics for presentation."""
    summaries = db.query(DailySummary).all()
    events = db.query(RiskEvent).all()
    
    total_breaker_triggers = sum(s.breaker_triggers_count for s in summaries)
    max_overall_drawdown = max((s.max_intraday_drawdown for s in summaries), default=0.0)
    
    # Calculate simple stats
    pnl_values = [s.realized_pnl + s.unrealized_pnl for s in summaries]
    total_pnl = sum(pnl_values)
    net_win_days = sum(1 for p in pnl_values if p > 0)
    total_days = len(summaries)
    
    # Estimate capital savings (e.g. ₹10k per trigger saved on average)
    estimated_savings = total_breaker_triggers * 15000.0
    
    return {
        "totalBreakerTriggers": total_breaker_triggers,
        "maxDrawdown": max_overall_drawdown,
        "netPnL": round(total_pnl, 2),
        "winRateDays": round((net_win_days / total_days * 100), 2) if total_days > 0 else 0.0,
        "estimatedSavings": estimated_savings,
        "daysTracked": total_days
    }
