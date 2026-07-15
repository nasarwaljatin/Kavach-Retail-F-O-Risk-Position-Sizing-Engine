from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict

from app.db.session import get_db
from app.broker.angelone import AngelOneBroker
from app.models.position import PositionSnapshot

router = APIRouter(prefix="/api/positions", tags=["positions"])
broker = AngelOneBroker()

@router.get("/")
def get_live_positions():
    """Get active live positions from the broker."""
    try:
        if not broker.authenticated:
            broker.authenticate()
        positions = broker.get_positions()
        return [
            {
                "symbol": p.symbol,
                "exchange": p.exchange,
                "qty": p.qty,
                "avgPrice": p.avg_price,
                "ltp": p.ltp,
                "pnl": p.pnl,
                "productType": p.product_type,
                "instrumentType": p.instrument_type,
                "exposure": p.exposure
            }
            for p in positions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch live positions: {str(e)}")

@router.get("/history")
def get_positions_history(hours: int = 24, db: Session = Depends(get_db)):
    """Fetch database snapshot history of positions."""
    since = datetime.utcnow() - timedelta(hours=hours)
    snapshots = db.query(PositionSnapshot).filter(PositionSnapshot.ts >= since).order_by(PositionSnapshot.ts.desc()).all()
    
    # Format snapshots grouped by timestamp or just return list
    return [
        {
            "id": s.id,
            "ts": s.ts.isoformat() + "Z",
            "symbol": s.symbol,
            "qty": s.qty,
            "ltp": s.ltp,
            "exposure": s.exposure,
            "unrealizedPnl": s.unrealized_pnl,
            "marginUsed": s.margin_used
        }
        for s in snapshots
    ]
