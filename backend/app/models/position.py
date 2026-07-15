from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.session import Base

class PositionSnapshot(Base):
    __tablename__ = "positions_snapshot"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    symbol = Column(String(50), nullable=False)
    qty = Column(Integer, nullable=False)
    ltp = Column(Float, nullable=False)
    exposure = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    margin_used = Column(Float, nullable=False)
