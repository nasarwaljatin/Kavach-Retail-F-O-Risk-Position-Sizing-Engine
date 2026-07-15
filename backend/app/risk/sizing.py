import logging

logger = logging.getLogger("kavach.risk.sizing")

def fractional_kelly_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    capital: float,
    kelly_multiplier: float = 0.3
) -> float:
    """
    Computes position size as a fraction of the Kelly Criterion.
    
    b = payoff ratio (avg win / avg loss)
    Full Kelly f* = (b*p - q) / b
    kelly_multiplier < 1 (typically 0.3 or 0.25) to avoid noise sensitivity
    """
    if avg_loss <= 0:
        logger.warning("Average loss must be positive and non-zero. Sizing set to 0.")
        return 0.0
    if win_rate < 0 or win_rate > 1:
        logger.warning("Win rate must be between 0 and 1. Sizing set to 0.")
        return 0.0
    if capital <= 0:
        return 0.0

    b = avg_win / avg_loss
    p = win_rate
    q = 1.0 - p

    if b <= 0:
        return 0.0

    # f* = (b*p - q) / b = (bp - (1-p)) / b = (bp - 1 + p) / b
    full_kelly = (b * p - q) / b
    fractional_kelly = max(full_kelly * kelly_multiplier, 0.0)

    # Size = capital * f*
    return capital * fractional_kelly

def volatility_adjusted_size(
    capital: float,
    risk_per_trade_pct: float,
    atr: float,
    stop_distance_multiple: float = 1.5
) -> float:
    """
    Sizes so a stop-out at (stop_distance_multiple * ATR) loses exactly
    risk_per_trade_pct of capital.
    
    Returns raw position quantity.
    """
    if atr <= 0:
        logger.warning("ATR must be greater than zero. Sizing set to 0.")
        return 0.0
    if risk_per_trade_pct <= 0 or capital <= 0:
        return 0.0
    if stop_distance_multiple <= 0:
        logger.warning("Stop distance multiple must be greater than zero. Sizing set to 0.")
        return 0.0

    risk_amount = capital * (risk_per_trade_pct / 100.0)
    stop_distance = atr * stop_distance_multiple
    
    return risk_amount / stop_distance

def compute_position_size(
    capital: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    atr: float,
    risk_per_trade_pct: float = 1.0,
    kelly_multiplier: float = 0.3,
    stop_distance_multiple: float = 1.5,
    lot_size: int = 1
) -> dict:
    """
    Sizes using both Kelly and Volatility-adjusted methods.
    Returns the minimum of the two to maintain conservative risk management.
    """
    k_size = fractional_kelly_size(
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        capital=capital,
        kelly_multiplier=kelly_multiplier
    )

    v_size = volatility_adjusted_size(
        capital=capital,
        risk_per_trade_pct=risk_per_trade_pct,
        atr=atr,
        stop_distance_multiple=stop_distance_multiple
    )

    # Take the more conservative size
    recommended = min(k_size, v_size)
    
    # Quantize into lots
    lots = int(recommended // lot_size) if lot_size > 0 else 0
    lots = max(lots, 0)
    total_qty = lots * lot_size

    return {
        "kelly_qty": round(k_size, 2),
        "vol_adjusted_qty": round(v_size, 2),
        "recommended_qty": round(recommended, 2),
        "lots": lots,
        "total_qty": total_qty
    }
