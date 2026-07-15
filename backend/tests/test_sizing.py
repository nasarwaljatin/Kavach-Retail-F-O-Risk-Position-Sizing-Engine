import pytest
from app.risk.sizing import fractional_kelly_size, volatility_adjusted_size, compute_position_size

def test_fractional_kelly_basic():
    # payoff b = 2.0 (avg_win / avg_loss = 100 / 50)
    # win_rate p = 0.6
    # q = 0.4
    # Full Kelly f* = (2.0 * 0.6 - 0.4) / 2.0 = (1.2 - 0.4) / 2.0 = 0.8 / 2.0 = 0.4
    # Fractional Kelly (multiplier 0.3) = 0.4 * 0.3 = 0.12
    # Capital = 100,000 -> size = 12,000
    size = fractional_kelly_size(
        win_rate=0.6,
        avg_win=100.0,
        avg_loss=50.0,
        capital=100000.0,
        kelly_multiplier=0.3
    )
    assert abs(size - 12000.0) < 1e-5

def test_fractional_kelly_no_edge():
    # win_rate p = 0.3
    # q = 0.7
    # payoff b = 1.0 (payoff = 1:1)
    # Full Kelly = (1 * 0.3 - 0.7) / 1 = -0.4 -> should cap at 0
    size = fractional_kelly_size(
        win_rate=0.3,
        avg_win=50.0,
        avg_loss=50.0,
        capital=100000.0,
        kelly_multiplier=0.3
    )
    assert size == 0.0

def test_volatility_adjusted_basic():
    # Capital = 100,000
    # Risk % = 1% -> risk amount = 1,000
    # ATR = 100.0, multiple = 2.0 -> stop distance = 200.0
    # Qty = 1,000 / 200 = 5.0
    size = volatility_adjusted_size(
        capital=100000.0,
        risk_per_trade_pct=1.0,
        atr=100.0,
        stop_distance_multiple=2.0
    )
    assert size == 5.0

def test_volatility_adjusted_zero_atr():
    # ATR = 0 -> should handle gracefully and return 0
    size = volatility_adjusted_size(
        capital=100000.0,
        risk_per_trade_pct=1.0,
        atr=0.0,
        stop_distance_multiple=2.0
    )
    assert size == 0.0

def test_compute_position_size():
    # Kelly gives 12,000 (computed above)
    # Volatility adjusted:
    # Capital = 100,000, risk = 2% -> risk_amount = 2,000
    # ATR = 50.0, stop mult = 1.5 -> stop_distance = 75.0
    # Vol size = 2000 / 75 = 26.67
    # recommended should be min(12000, 26.67) = 26.67
    # with lot_size 5, lots = 26.67 // 5 = 5. Total qty = 25
    res = compute_position_size(
        capital=100000.0,
        win_rate=0.6,
        avg_win=100.0,
        avg_loss=50.0,
        atr=50.0,
        risk_per_trade_pct=2.0,
        kelly_multiplier=0.3,
        stop_distance_multiple=1.5,
        lot_size=5
    )
    assert res["recommended_qty"] == pytest.approx(26.67, 0.01)
    assert res["lots"] == 5
    assert res["total_qty"] == 25
