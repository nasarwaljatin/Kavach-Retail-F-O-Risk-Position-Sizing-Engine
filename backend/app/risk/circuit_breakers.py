import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

logger = logging.getLogger("kavach.risk.circuit_breakers")

@dataclass
class PositionState:
    symbol: str
    exposure: float

@dataclass
class AccountState:
    capital_base: float
    day_pnl: float
    margin_utilisation_pct: float
    positions: List[PositionState] = field(default_factory=list)
    orders_in_last_10min: int = 0
    is_expiry_day: bool = False
    new_position_size: float = 0.0
    baseline_position_size: float = 0.0

@dataclass
class BreakerConfig:
    max_daily_loss_pct: float = 2.0
    max_margin_utilisation_pct: float = 70.0
    max_position_concentration_pct: float = 20.0
    order_velocity_limit_per_10min: int = 5
    expiry_day_size_dampener: float = 0.5

def is_expiry_day(dt: datetime) -> bool:
    """
    Checks if a given date is an F&O expiry day.
    In India:
    - Nifty / NFO weekly options expire on Thursdays.
    - Bank Nifty weekly options expire on Wednesdays.
    - Monthly contracts expire on the last Thursday of the month.
    """
    # 2 is Wednesday, 3 is Thursday (0-indexed starting Monday)
    day_of_week = dt.weekday()
    return day_of_week in (2, 3)

def check_circuit_breakers(account_state: AccountState, config: BreakerConfig) -> List[str]:
    """
    Checks the current account state against risk rules and limits.
    Returns list of triggered breaker codes.
    """
    triggered = []

    if account_state.capital_base <= 0:
        logger.warning("Capital base is zero or negative. Blocking trading.")
        triggered.append("DAILY_LOSS_LIMIT")
        return triggered

    # 1. Daily Loss Limit Check
    # day_pnl is negative for loss. So if day_pnl <= - (capital_base * daily_loss_pct / 100)
    daily_loss_pct = (account_state.day_pnl / account_state.capital_base) * 100
    if daily_loss_pct <= -config.max_daily_loss_pct:
        triggered.append("DAILY_LOSS_LIMIT")

    # 2. Margin Utilisation Check
    if account_state.margin_utilisation_pct >= config.max_margin_utilisation_pct:
        triggered.append("MARGIN_CAP")

    # 3. Position Concentration Check
    for pos in account_state.positions:
        concentration_pct = (pos.exposure / account_state.capital_base) * 100
        if concentration_pct >= config.max_position_concentration_pct:
            triggered.append(f"CONCENTRATION_{pos.symbol}")

    # 4. Order Velocity Check (Revenge trading safeguard)
    if account_state.orders_in_last_10min >= config.order_velocity_limit_per_10min:
        triggered.append("ORDER_VELOCITY_REVENGE_TRADING")

    # 5. Expiry Day Sizing Dampener Check
    if account_state.is_expiry_day:
        dampened_max_size = account_state.baseline_position_size * config.expiry_day_size_dampener
        if account_state.new_position_size > dampened_max_size:
            triggered.append("EXPIRY_DAY_OVERSIZE")

    return triggered
