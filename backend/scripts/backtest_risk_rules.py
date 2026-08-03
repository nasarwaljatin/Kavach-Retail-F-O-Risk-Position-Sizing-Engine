#!/usr/bin/env python3
"""
Kavach Backtest Risk Rules Validator
=====================================
Replays historical trades through the configured circuit breakers and reports:
  1. Days that would have been circuit-broken (count + dates)
  2. Estimated rupee losses those breakers would have prevented
  3. Max drawdown before vs. after breakers applied

Usage:
    python scripts/backtest_risk_rules.py --csv scripts/sample_trades.csv --capital 100000

CSV columns required (headers):
    date, symbol, side, qty, entry_price, exit_price, pnl

Example:
    2026-01-15,NIFTY26JAN2519800CE,BUY,50,145.50,98.30,-2360.00

The script does NOT import any DB or broker code — pure risk logic only.
"""

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, NamedTuple

# Force UTF-8 output on Windows to prevent cp1252 encoding errors
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass

# Allow running from repo root or scripts/ dir
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from app.risk.circuit_breakers import (
    AccountState,
    BreakerConfig,
    PositionState,
    check_circuit_breakers,
)
from app.risk.expiry_calendar import is_expiry_day


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class TradeRow(NamedTuple):
    date: date
    symbol: str
    side: str
    qty: int
    entry_price: float
    exit_price: float
    pnl: float


class DaySummary(NamedTuple):
    date: date
    trades: List[TradeRow]
    cumulative_pnl: float          # P&L summed over all trades that day
    would_be_stopped: bool         # did a breaker fire?
    stopped_at_pnl: float          # P&L at the point breaker fired (0 if not stopped)
    breakers_triggered: List[str]
    losses_prevented: float        # |pnl_after_stop - cumulative_pnl| if stopped, else 0


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_trades(csv_path: str) -> List[TradeRow]:
    rows: List[TradeRow] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"date", "symbol", "side", "qty", "entry_price", "exit_price", "pnl"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"[ERROR] CSV missing required columns: {missing}")
            sys.exit(1)
        for i, row in enumerate(reader, 2):
            try:
                rows.append(TradeRow(
                    date=date.fromisoformat(row["date"].strip()),
                    symbol=row["symbol"].strip(),
                    side=row["side"].strip().upper(),
                    qty=int(row["qty"]),
                    entry_price=float(row["entry_price"]),
                    exit_price=float(row["exit_price"]),
                    pnl=float(row["pnl"]),
                ))
            except (ValueError, KeyError) as exc:
                print(f"[WARN] Skipping row {i}: {exc}")
    return rows


# ---------------------------------------------------------------------------
# Replay engine
# ---------------------------------------------------------------------------

def replay_day(
    trade_date: date,
    trades: List[TradeRow],
    capital: float,
    config: BreakerConfig,
) -> DaySummary:
    """
    Simulate trading through a single day trade-by-trade.
    Check circuit breakers after each trade.
    Once a breaker fires, remaining trades are halted.
    """
    cumulative_pnl = 0.0
    stopped = False
    stopped_at = 0.0
    breakers: List[str] = []

    # Build a running position map for concentration check
    # (simplified: each trade is its own position, full exposure = entry_price * qty)
    position_map: Dict[str, float] = {}

    for trade in trades:
        if stopped:
            break

        cumulative_pnl += trade.pnl

        # Update exposure for this symbol (long only for simplicity)
        exposure = trade.entry_price * trade.qty
        position_map[trade.symbol] = position_map.get(trade.symbol, 0.0) + exposure

        pos_states = [
            PositionState(symbol=sym, exposure=exp)
            for sym, exp in position_map.items()
        ]

        account = AccountState(
            capital_base=capital,
            day_pnl=cumulative_pnl,
            margin_utilisation_pct=min(
                sum(position_map.values()) / capital * 100 if capital > 0 else 0,
                100,
            ),
            positions=pos_states,
            orders_in_last_10min=0,
            is_expiry_day=is_expiry_day(datetime.combine(trade_date, datetime.min.time())),
        )

        fired = check_circuit_breakers(account, config)
        if fired:
            stopped = True
            stopped_at = cumulative_pnl
            breakers = fired
            break

    losses_prevented = 0.0
    if stopped:
        # Sum remaining trades that were halted
        idx = trades.index(trade)  # type: ignore[name-defined]
        remaining_pnl = sum(t.pnl for t in trades[idx + 1:])
        losses_prevented = max(-remaining_pnl, 0.0)

    return DaySummary(
        date=trade_date,
        trades=trades,
        cumulative_pnl=cumulative_pnl,
        would_be_stopped=stopped,
        stopped_at_pnl=stopped_at,
        breakers_triggered=breakers,
        losses_prevented=losses_prevented,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kavach — backtest circuit breakers against historical trades"
    )
    parser.add_argument("--csv", required=True, help="Path to trades CSV file")
    parser.add_argument("--capital", type=float, default=100_000.0,
                        help="Starting capital in INR (default: 100000)")
    parser.add_argument("--max-daily-loss-pct", type=float, default=2.0,
                        help="Max daily loss %% (default: 2.0)")
    parser.add_argument("--max-margin-pct", type=float, default=70.0,
                        help="Max margin utilisation %% (default: 70.0)")
    parser.add_argument("--max-concentration-pct", type=float, default=20.0,
                        help="Max single position concentration %% (default: 20.0)")
    args = parser.parse_args()

    trades = load_trades(args.csv)
    if not trades:
        print("[ERROR] No trades loaded.")
        sys.exit(1)

    config = BreakerConfig(
        max_daily_loss_pct=args.max_daily_loss_pct,
        max_margin_utilisation_pct=args.max_margin_pct,
        max_position_concentration_pct=args.max_concentration_pct,
    )

    # Group by date
    by_date: Dict[date, List[TradeRow]] = defaultdict(list)
    for t in trades:
        by_date[t.date].append(t)

    results: List[DaySummary] = []
    for d in sorted(by_date.keys()):
        summary = replay_day(d, by_date[d], args.capital, config)
        results.append(summary)

    # --- Metrics ---
    total_days = len(results)
    stopped_days = [r for r in results if r.would_be_stopped]
    total_pnl_no_breaker = sum(r.cumulative_pnl for r in results)
    total_losses_prevented = sum(r.losses_prevented for r in stopped_days)

    # Drawdown before breakers: running cumulative P&L series
    equity_before = []
    running = 0.0
    for r in results:
        running += r.cumulative_pnl
        equity_before.append(running)
    max_before = max(equity_before) if equity_before else 0
    drawdown_before = min(0, min(
        equity_before[i] - max(equity_before[:i + 1])
        for i in range(len(equity_before))
    )) if equity_before else 0

    # Drawdown after breakers: use stopped_at_pnl when stopped
    equity_after = []
    running = 0.0
    for r in results:
        day_pnl = r.stopped_at_pnl if r.would_be_stopped else r.cumulative_pnl
        running += day_pnl
        equity_after.append(running)
    max_after = max(equity_after) if equity_after else 0
    drawdown_after = min(0, min(
        equity_after[i] - max(equity_after[:i + 1])
        for i in range(len(equity_after))
    )) if equity_after else 0

    # --- Print report ---
    sep = "=" * 62
    print(f"\n{sep}")
    print("  KAVACH BACKTEST — Circuit Breaker Validation Report")
    print(sep)
    print(f"  CSV                  : {args.csv}")
    print(f"  Capital              : ₹{args.capital:,.0f}")
    print(f"  Total trading days   : {total_days}")
    print(f"  Trades loaded        : {len(trades)}")
    print(f"  Config               :")
    print(f"    Max daily loss     : {args.max_daily_loss_pct}%")
    print(f"    Max margin util    : {args.max_margin_pct}%")
    print(f"    Max concentration  : {args.max_concentration_pct}%")
    print(sep)
    print(f"  Days circuit-broken  : {len(stopped_days)} of {total_days}")
    if stopped_days:
        for s in stopped_days:
            print(f"    {s.date}  breakers={s.breakers_triggered}  "
                  f"P&L at stop=₹{s.stopped_at_pnl:,.2f}")
    print()
    print(f"  Total P&L (no brk)   : ₹{total_pnl_no_breaker:,.2f}")
    print(f"  Est. losses prevented: ₹{total_losses_prevented:,.2f}  ← the number that matters")
    print()
    print(f"  Max drawdown before  : ₹{drawdown_before:,.2f}")
    print(f"  Max drawdown after   : ₹{drawdown_after:,.2f}")
    improvement = drawdown_before - drawdown_after
    print(f"  Drawdown improvement : ₹{improvement:,.2f}")
    print(sep)
    print()


if __name__ == "__main__":
    main()
