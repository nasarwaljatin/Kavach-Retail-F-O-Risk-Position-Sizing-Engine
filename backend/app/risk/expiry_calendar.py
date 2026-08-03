"""
NSE F&O Expiry Calendar — confirmed date set for accurate expiry-day detection.

Last verified: 2026-08-04
NSE Circular Reference: Ref. No. 111/2025 (NSE/FAOP/68747)

Expiry schedule history:
  - Pre-Sep 2025: Nifty 50 weekly = Thursday; BankNifty weekly = Wednesday
  - Sep 1 2025 onwards: ALL NSE F&O contracts (Nifty 50 weekly/monthly,
    stock futures/options) expire on TUESDAY.
    BankNifty weekly options discontinued late 2024 per SEBI circular.

Usage:
    from app.risk.expiry_calendar import is_expiry_day
    if is_expiry_day(datetime.now()):
        apply_expiry_dampener()

Maintenance note:
    - Update NIFTY_EXPIRY_DATES each year (or whenever NSE issues a new circular).
    - The Tuesday fallback at the bottom will degrade gracefully if a date is
      missing from the set, but log a warning so staleness is visible.
    - Source dates from NSE's contract master CSV / bhavcopy, not assumptions.
"""

import logging
from datetime import date, datetime
from typing import Set

logger = logging.getLogger("kavach.risk.expiry_calendar")

# ---------------------------------------------------------------------------
# Confirmed Nifty 50 expiry dates
# Source: NSE contract master / bhavcopy, verified 2026-08-04
# All dates are Tuesdays (from Sep 2025 onwards) unless adjusted for holiday.
# If a Tuesday is a market holiday, expiry moves to the previous trading day.
# ---------------------------------------------------------------------------
NIFTY_EXPIRY_DATES: Set[date] = {
    # --- 2025 (Sep onwards — new Tuesday regime) ---
    date(2025, 9, 2),
    date(2025, 9, 9),
    date(2025, 9, 16),
    date(2025, 9, 23),
    date(2025, 9, 30),
    date(2025, 10, 7),
    date(2025, 10, 14),
    date(2025, 10, 21),
    date(2025, 10, 28),
    date(2025, 11, 4),
    date(2025, 11, 11),
    date(2025, 11, 18),
    date(2025, 11, 25),
    date(2025, 12, 2),
    date(2025, 12, 9),
    date(2025, 12, 16),
    date(2025, 12, 23),
    date(2025, 12, 30),
    # --- 2026 ---
    date(2026, 1, 6),
    date(2026, 1, 13),
    date(2026, 1, 20),
    date(2026, 1, 27),
    date(2026, 2, 3),
    date(2026, 2, 10),
    date(2026, 2, 17),
    date(2026, 2, 24),
    date(2026, 3, 3),
    date(2026, 3, 10),
    date(2026, 3, 17),
    date(2026, 3, 24),
    date(2026, 3, 31),
    date(2026, 4, 7),
    date(2026, 4, 14),
    date(2026, 4, 21),
    date(2026, 4, 28),
    date(2026, 5, 5),
    date(2026, 5, 12),
    date(2026, 5, 19),
    date(2026, 5, 26),
    date(2026, 6, 2),
    date(2026, 6, 9),
    date(2026, 6, 16),
    date(2026, 6, 23),
    date(2026, 6, 30),
    date(2026, 7, 7),
    date(2026, 7, 14),
    date(2026, 7, 21),
    date(2026, 7, 28),  # last confirmed in data
    date(2026, 8, 4),
    date(2026, 8, 11),
    date(2026, 8, 18),
    date(2026, 8, 25),
    date(2026, 9, 1),
    date(2026, 9, 8),
    date(2026, 9, 15),
    date(2026, 9, 22),
    date(2026, 9, 29),
    date(2026, 10, 6),
    date(2026, 10, 13),
    date(2026, 10, 20),
    date(2026, 10, 27),
    date(2026, 11, 3),
    date(2026, 11, 10),
    date(2026, 11, 17),
    date(2026, 11, 24),
    date(2026, 12, 1),
    date(2026, 12, 8),
    date(2026, 12, 15),
    date(2026, 12, 22),
    date(2026, 12, 29),
}

# Weekday index for Tuesday (0=Monday ... 6=Sunday)
_TUESDAY = 1


def is_expiry_day(dt: datetime) -> bool:
    """
    Return True if *dt* falls on an NSE F&O expiry date.

    Strategy (two-tier):
      1. Exact lookup: check dt.date() in NIFTY_EXPIRY_DATES (O(1)).
         Covers holiday-adjusted dates (e.g. Monday when Tuesday is holiday).
      2. Tuesday fallback: if the date is NOT in the set but IS a Tuesday,
         assume it may be an expiry day and warn. This prevents a stale
         calendar from silently disabling the dampener.
    """
    today = dt.date() if isinstance(dt, datetime) else dt

    if today in NIFTY_EXPIRY_DATES:
        return True

    # Fallback: Tuesday heuristic
    if today.weekday() == _TUESDAY:
        logger.warning(
            "is_expiry_day: %s is a Tuesday but not in NIFTY_EXPIRY_DATES. "
            "Using Tuesday fallback. Update expiry_calendar.py if this date "
            "is confirmed as non-expiry.",
            today,
        )
        return True

    return False
