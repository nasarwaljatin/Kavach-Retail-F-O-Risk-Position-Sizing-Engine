from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

from app.db.session import get_db
from app.broker.angelone import AngelOneBroker
from app.models.risk_event import RiskEvent
from app.models.risk_config import RiskConfig
from app.risk.sizing import compute_position_size as core_compute_size
from app.risk.rules_config import get_all_config, set_config_value

router = APIRouter(prefix="/api/risk", tags=["risk"])
broker = AngelOneBroker()

class SizingRequest(BaseModel):
    capital: float
    winRate: float
    avgWin: float
    avgLoss: float
    atr: float
    riskPerTradePct: Optional[float] = 1.0
    kellyMultiplier: Optional[float] = 0.3
    stopDistanceMultiple: Optional[float] = 1.5
    lotSize: Optional[int] = 1

class ConfigUpdateRequest(BaseModel):
    maxDailyLossPct: Optional[float] = None
    maxPositionConcentrationPct: Optional[float] = None
    maxMarginUtilisationPct: Optional[float] = None
    kellyFractionMultiplier: Optional[float] = None
    orderVelocityLimitPer10Min: Optional[int] = None
    expiryDaySizeDampener: Optional[float] = None

@router.get("/state")
def get_risk_state():
    """Get overall live risk state summary."""
    try:
        if not broker.authenticated:
            broker.authenticate()
        positions = broker.get_positions()
        margins = broker.get_margins()
        
        capital_base = margins.net if margins.net > 0 else 100000.0
        day_pnl = margins.unrealized_mtm + margins.realized_mtm
        
        return {
            "capitalBase": capital_base,
            "dayPnl": round(day_pnl, 2),
            "dayPnlPct": round((day_pnl / capital_base) * 100, 2) if capital_base > 0 else 0.0,
            "marginUtilisationPct": round(margins.utilisation_pct, 2),
            "riskLevel": "safe" if margins.utilisation_pct < 50 else "warning" if margins.utilisation_pct < 80 else "danger",
            "lastUpdated": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch risk state: {str(e)}")

@router.get("/events")
def get_risk_events(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Fetch logged circuit breaker events."""
    events = db.query(RiskEvent).order_by(RiskEvent.ts.desc()).limit(limit).offset(offset).all()
    return [
        {
            "id": e.id,
            "ts": e.ts.isoformat() + "Z",
            "breakerType": e.breaker_type,
            "details": e.details_json,
            "actionTaken": e.action_taken
        }
        for e in events
    ]

@router.get("/config")
def get_risk_config(db: Session = Depends(get_db)):
    """Get active risk configs from the database."""
    config_dict = get_all_config(db)
    # Ensure UI-friendly casing
    return {
        "maxDailyLossPct": config_dict.get("MAX_DAILY_LOSS_PCT", 2.0),
        "maxPositionConcentrationPct": config_dict.get("MAX_POSITION_CONCENTRATION_PCT", 20.0),
        "maxMarginUtilisationPct": config_dict.get("MAX_MARGIN_UTILISATION_PCT", 70.0),
        "kellyFractionMultiplier": config_dict.get("KELLY_FRACTION_MULTIPLIER", 0.3),
        "orderVelocityLimitPer10Min": config_dict.get("ORDER_VELOCITY_LIMIT_PER_10MIN", 5),
        "expiryDaySizeDampener": config_dict.get("EXPIRY_DAY_SIZE_DAMPENER", 0.5)
    }

@router.put("/config")
def update_risk_config(payload: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """Update risk configuration values."""
    if payload.maxDailyLossPct is not None:
        set_config_value(db, "MAX_DAILY_LOSS_PCT", payload.maxDailyLossPct)
    if payload.maxPositionConcentrationPct is not None:
        set_config_value(db, "MAX_POSITION_CONCENTRATION_PCT", payload.maxPositionConcentrationPct)
    if payload.maxMarginUtilisationPct is not None:
        set_config_value(db, "MAX_MARGIN_UTILISATION_PCT", payload.maxMarginUtilisationPct)
    if payload.kellyFractionMultiplier is not None:
        set_config_value(db, "KELLY_FRACTION_MULTIPLIER", payload.kellyFractionMultiplier)
    if payload.orderVelocityLimitPer10Min is not None:
        set_config_value(db, "ORDER_VELOCITY_LIMIT_PER_10MIN", payload.orderVelocityLimitPer10Min)
    if payload.expiryDaySizeDampener is not None:
        set_config_value(db, "EXPIRY_DAY_SIZE_DAMPENER", payload.expiryDaySizeDampener)
        
    return {"status": "success", "message": "Risk configuration updated successfully"}

@router.post("/size")
def calculate_size(payload: SizingRequest):
    """Calculate recommended position size using Kelly and Volatility methods."""
    try:
        result = core_compute_size(
            capital=payload.capital,
            win_rate=payload.winRate,
            avg_win=payload.avgWin,
            avg_loss=payload.avgLoss,
            atr=payload.atr,
            risk_per_trade_pct=payload.riskPerTradePct,
            kelly_multiplier=payload.kellyMultiplier,
            stop_distance_multiple=payload.stopDistanceMultiple,
            lot_size=payload.lotSize
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")
