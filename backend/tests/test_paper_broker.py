"""
Tests for PaperBrokerAdapter and get_broker() factory.

Uses SQLite in-memory DB to avoid needing a real Postgres instance.
No real Angel One API calls are made.
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.broker.base import BaseBroker, Position, MarginData, OrderParams, OrderResult
from app.broker.paper import PaperBrokerAdapter


# ---------------------------------------------------------------------------
# In-memory SQLite fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# Fake inner broker
# ---------------------------------------------------------------------------

def _make_fake_broker() -> MagicMock:
    fake = MagicMock(spec=BaseBroker)
    fake.authenticate.return_value = True
    fake.get_positions.return_value = [
        Position(
            symbol="NIFTY26AUG2623500CE",
            exchange="NFO",
            qty=50,
            avg_price=120.0,
            ltp=135.0,
            pnl=750.0,
            product_type="CARRYFORWARD",
            instrument_type="CE",
            symbol_token="26009",
            exposure=6750.0,
        )
    ]
    fake.get_margins.return_value = MarginData(
        net=100000.0,
        available_cash=85000.0,
        used_margin=15000.0,
        collateral=0.0,
        unrealized_mtm=750.0,
        realized_mtm=0.0,
        utilisation_pct=15.0,
    )
    fake.get_quote.return_value = {"ltp": 135.0}
    fake.get_order_book.return_value = []
    return fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPaperBrokerAdapter:
    def test_place_order_does_not_call_real_broker(self, db_session):
        fake = _make_fake_broker()
        adapter = PaperBrokerAdapter(fake)

        params = OrderParams(
            symbol="NIFTY26AUG2623500CE",
            exchange="NFO",
            transaction_type="SELL",
            order_type="MARKET",
            product_type="CARRYFORWARD",
            quantity=50,
            symbol_token="26009",
        )

        with patch("app.broker.paper.SessionLocal", return_value=db_session):
            result = adapter.place_order(params)

        # Real broker's placeOrder must never be called
        fake.place_order.assert_not_called()
        assert result.status == "SUCCESS"
        assert "PAPER" in result.order_id

    def test_place_order_writes_to_db(self, db_session):
        from app.models.paper_order import PaperOrder

        fake = _make_fake_broker()
        adapter = PaperBrokerAdapter(fake)

        params = OrderParams(
            symbol="RELIANCE-EQ",
            exchange="NSE",
            transaction_type="BUY",
            order_type="MARKET",
            product_type="INTRADAY",
            quantity=10,
            price=0.0,
        )

        with patch("app.broker.paper.SessionLocal", return_value=db_session):
            adapter.place_order(params)

        rows = db_session.query(PaperOrder).filter(
            PaperOrder.symbol == "RELIANCE-EQ"
        ).all()
        assert len(rows) >= 1
        assert rows[-1].transaction_type == "BUY"

    def test_square_off_all_does_not_call_real_broker(self, db_session):
        fake = _make_fake_broker()
        adapter = PaperBrokerAdapter(fake)

        with patch("app.broker.paper.SessionLocal", return_value=db_session):
            results = adapter.square_off_all()

        # Real broker square_off_all must NOT be called
        fake.square_off_all.assert_not_called()
        # Should have produced one exit order (for the single mock position)
        assert len(results) == 1
        assert results[0].status == "SUCCESS"

    def test_read_methods_delegate_to_real_broker(self):
        fake = _make_fake_broker()
        adapter = PaperBrokerAdapter(fake)

        positions = adapter.get_positions()
        margins = adapter.get_margins()
        quote = adapter.get_quote("NFO", "NIFTY26AUG2623500CE", "26009")

        fake.get_positions.assert_called_once()
        fake.get_margins.assert_called_once()
        fake.get_quote.assert_called_once()
        assert len(positions) == 1
        assert margins.net == 100000.0
        assert quote["ltp"] == 135.0

    def test_authenticate_delegates(self):
        fake = _make_fake_broker()
        adapter = PaperBrokerAdapter(fake)
        assert adapter.authenticate() is True
        fake.authenticate.assert_called_once()


class TestBrokerFactory:
    def test_paper_mode_true_returns_paper_adapter(self):
        from app.broker.factory import get_broker

        with patch("app.broker.factory.settings") as mock_settings:
            mock_settings.PAPER_MODE = True
            broker = get_broker()

        assert isinstance(broker, PaperBrokerAdapter)

    def test_paper_mode_false_returns_angelone(self):
        from app.broker.factory import get_broker
        from app.broker.angelone import AngelOneBroker

        with patch("app.broker.factory.settings") as mock_settings:
            mock_settings.PAPER_MODE = False
            broker = get_broker()

        assert isinstance(broker, AngelOneBroker)
