"""SQLAlchemy model for paper trading order log."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from app.db.session import Base


class PaperOrder(Base):
    """
    Records every order that PaperBrokerAdapter would have placed in live mode.
    Used to verify no real orders leaked through during paper-mode runs.
    """
    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(10), nullable=False)
    transaction_type = Column(String(10), nullable=False)   # BUY / SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False, default=0.0)
    order_type = Column(String(20), nullable=False)         # MARKET / LIMIT
    product_type = Column(String(20), nullable=False)       # INTRADAY / CARRYFORWARD
    symbol_token = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="PAPER_COMPLETE")
    fill_price = Column(Float, nullable=True)               # simulated fill (= ltp at time of order)
    notes = Column(Text, nullable=True)                     # e.g. "square_off_all triggered"
