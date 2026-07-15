import pytest
from app.risk.circuit_breakers import (
    AccountState,
    PositionState,
    BreakerConfig,
    check_circuit_breakers
)

def test_no_breakers_triggered():
    state = AccountState(
        capital_base=100000.0,
        day_pnl=-500.0,  # -0.5% loss
        margin_utilisation_pct=30.0,
        positions=[
            PositionState(symbol="RELIANCE-EQ", exposure=5000.0),
            PositionState(symbol="NIFTY-CE", exposure=8000.0)
        ],
        orders_in_last_10min=2,
        is_expiry_day=False
    )
    config = BreakerConfig(
        max_daily_loss_pct=2.0,
        max_margin_utilisation_pct=70.0,
        max_position_concentration_pct=20.0,
        order_velocity_limit_per_10min=5,
        expiry_day_size_dampener=0.5
    )
    triggered = check_circuit_breakers(state, config)
    assert len(triggered) == 0

def test_daily_loss_limit_triggered():
    state = AccountState(
        capital_base=100000.0,
        day_pnl=-2500.0,  # -2.5% loss (exceeds 2.0%)
        margin_utilisation_pct=30.0,
        positions=[],
        orders_in_last_10min=1
    )
    config = BreakerConfig(max_daily_loss_pct=2.0)
    triggered = check_circuit_breakers(state, config)
    assert "DAILY_LOSS_LIMIT" in triggered

def test_margin_cap_triggered():
    state = AccountState(
        capital_base=100000.0,
        day_pnl=0.0,
        margin_utilisation_pct=75.0,  # exceeds 70%
        positions=[]
    )
    config = BreakerConfig(max_margin_utilisation_pct=70.0)
    triggered = check_circuit_breakers(state, config)
    assert "MARGIN_CAP" in triggered

def test_position_concentration_triggered():
    state = AccountState(
        capital_base=100000.0,
        day_pnl=0.0,
        margin_utilisation_pct=30.0,
        positions=[
            PositionState(symbol="SBIN-EQ", exposure=25000.0),  # 25% exposure (exceeds 20%)
            PositionState(symbol="RELIANCE-EQ", exposure=5000.0)
        ]
    )
    config = BreakerConfig(max_position_concentration_pct=20.0)
    triggered = check_circuit_breakers(state, config)
    assert "CONCENTRATION_SBIN-EQ" in triggered
    assert "CONCENTRATION_RELIANCE-EQ" not in triggered

def test_order_velocity_triggered():
    state = AccountState(
        capital_base=100000.0,
        day_pnl=0.0,
        margin_utilisation_pct=20.0,
        orders_in_last_10min=6  # exceeds 5
    )
    config = BreakerConfig(order_velocity_limit_per_10min=5)
    triggered = check_circuit_breakers(state, config)
    assert "ORDER_VELOCITY_REVENGE_TRADING" in triggered

def test_expiry_day_oversize_triggered():
    state = AccountState(
        capital_base=100000.0,
        day_pnl=0.0,
        margin_utilisation_pct=20.0,
        is_expiry_day=True,
        new_position_size=6000.0,       # 6% of capital
        baseline_position_size=10000.0  # dampener is 0.5 -> max allowed size is 5000.0 (5%)
    )
    config = BreakerConfig(expiry_day_size_dampener=0.5)
    triggered = check_circuit_breakers(state, config)
    assert "EXPIRY_DAY_OVERSIZE" in triggered
