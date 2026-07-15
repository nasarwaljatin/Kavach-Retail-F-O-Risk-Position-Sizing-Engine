from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.session import Base

class RiskConfig(Base):
    __tablename__ = "risk_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(255), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
