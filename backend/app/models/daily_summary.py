from sqlalchemy import Column, Integer, Float, Date
from app.db.session import Base

class DailySummary(Base):
    __tablename__ = "daily_summary"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    capital_base = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    max_intraday_drawdown = Column(Float, nullable=False)
    breaker_triggers_count = Column(Integer, default=0, nullable=False)
