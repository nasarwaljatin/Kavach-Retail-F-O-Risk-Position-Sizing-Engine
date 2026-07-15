from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.db.session import Base

class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    breaker_type = Column(String(50), nullable=False)
    details_json = Column(Text, nullable=False)  # JSON details of the breaker trigger
    action_taken = Column(String(20), nullable=False)  # alert, blocked, squared_off
