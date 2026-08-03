"""
Tests for InstrumentMaster token resolution.
No network calls — fixture data injected via load_from_records().
"""

import pytest
from app.broker.instrument_master import InstrumentMaster, resolve_token


FIXTURE_RECORDS = [
    {"token": "26009", "symbol": "NIFTY28OCT2524400CE", "exch_seg": "NFO"},
    {"token": "99926000", "symbol": "NIFTY50", "exch_seg": "NSE"},
    {"token": "1594", "symbol": "RELIANCE-EQ", "exch_seg": "NSE"},
    {"token": "35001", "symbol": "BANKNIFTY28OCT2551000PE", "exch_seg": "NFO"},
]


@pytest.fixture(autouse=True)
def fresh_master():
    """Reset singleton before each test to avoid state bleed."""
    InstrumentMaster.reset()
    master = InstrumentMaster.get()
    master.load_from_records(FIXTURE_RECORDS)
    yield master
    InstrumentMaster.reset()


class TestResolveToken:
    def test_known_nfo_symbol(self, fresh_master):
        token = fresh_master.resolve_token("NIFTY28OCT2524400CE", "NFO")
        assert token == "26009"

    def test_known_nse_symbol(self, fresh_master):
        token = fresh_master.resolve_token("RELIANCE-EQ", "NSE")
        assert token == "1594"

    def test_case_insensitive_lookup(self, fresh_master):
        token = fresh_master.resolve_token("nifty50", "nse")
        assert token == "99926000"

    def test_unknown_symbol_returns_empty_string(self, fresh_master):
        token = fresh_master.resolve_token("UNKNOWN123", "NFO")
        assert token == ""

    def test_exchange_mismatch_returns_empty_string(self, fresh_master):
        # RELIANCE-EQ is on NSE, not NFO
        token = fresh_master.resolve_token("RELIANCE-EQ", "NFO")
        assert token == ""

    def test_module_level_convenience_function(self, fresh_master):
        token = resolve_token("BANKNIFTY28OCT2551000PE", "NFO")
        assert token == "35001"

    def test_build_index_skips_empty_fields(self):
        InstrumentMaster.reset()
        m = InstrumentMaster.get()
        m.load_from_records([
            {"token": "", "symbol": "EMPTY", "exch_seg": "NSE"},        # no token
            {"token": "999", "symbol": "", "exch_seg": "NSE"},           # no symbol
            {"token": "888", "symbol": "VALID", "exch_seg": ""},         # no exchange
            {"token": "777", "symbol": "GOOD", "exch_seg": "NSE"},       # valid
        ])
        assert m.resolve_token("GOOD", "NSE") == "777"
        assert m.resolve_token("EMPTY", "NSE") == ""
        assert m.resolve_token("VALID", "NSE") == ""
