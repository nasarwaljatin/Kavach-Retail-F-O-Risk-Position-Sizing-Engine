from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from datetime import datetime

from app.db.session import get_db
from app.broker.angelone import AngelOneBroker
from app.models.risk_event import RiskEvent
from app.core.config import settings

router = APIRouter(prefix="/api/killswitch", tags=["killswitch"])
broker = AngelOneBroker()

@router.post("/")
def trigger_killswitch(db: Session = Depends(get_db)):
    """Trigger manual emergency square-off of all open positions."""
    try:
        if not broker.authenticated:
            broker.authenticate()

        # Call emergency square off
        results = broker.square_off_all()
        
        # Log to risk_events table
        details = {
            "source": "manual_dashboard_killswitch",
            "results": [r.__dict__ for r in results],
            "paper_mode": settings.PAPER_MODE
        }
        
        event = RiskEvent(
            breaker_type="MANUAL_KILL_SWITCH",
            details_json=json.dumps(details),
            action_taken="squared_off"
        )
        db.add(event)
        db.commit()

        return {
            "status": "success",
            "message": "Manual emergency square off executed successfully",
            "orders_placed": len(results)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to trigger killswitch: {str(e)}")

@router.get("/status")
def get_killswitch_status(db: Session = Depends(get_db)):
    """Check if the manual or automatic square-off was triggered today."""
    # Look for any MANUAL_KILL_SWITCH or DAILY_LOSS_LIMIT squared off events today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    event = db.query(RiskEvent).filter(
        RiskEvent.ts >= today_start,
        RiskEvent.action_taken == "squared_off"
    ).first()
    
    return {
        "killSwitchActive": event is not None,
        "triggeredAt": event.ts.isoformat() + "Z" if event else None,
        "reason": event.breaker_type if event else None
    }
