from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.session import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)  # BUY or SELL
    qty = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    instrument_type = Column(String(20), nullable=False)  # EQ, FUT, CE, PE
