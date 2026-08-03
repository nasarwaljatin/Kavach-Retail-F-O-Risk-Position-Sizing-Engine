"""
Tests for NSE expiry calendar.
"""

import pytest
from datetime import date, datetime
from unittest.mock import patch
import logging

from app.risk.expiry_calendar import is_expiry_day, NIFTY_EXPIRY_DATES


class TestExpiryCalendar:
    # Known confirmed Tuesday expiry dates
    def test_known_expiry_returns_true(self):
        # 2026-08-04 is in NIFTY_EXPIRY_DATES (Tuesday)
        dt = datetime(2026, 8, 4, 10, 30, 0)
        assert is_expiry_day(dt) is True

    def test_known_expiry_jan_2026(self):
        dt = datetime(2026, 1, 6, 9, 15, 0)
        assert is_expiry_day(dt) is True

    def test_non_expiry_weekday_returns_false(self):
        # 2026-08-05 is a Wednesday — not in set, not Tuesday
        dt = datetime(2026, 8, 5, 12, 0, 0)
        assert is_expiry_day(dt) is False

    def test_saturday_returns_false(self):
        # 2026-08-08 is a Saturday
        dt = datetime(2026, 8, 8, 10, 0, 0)
        assert is_expiry_day(dt) is False

    def test_monday_non_expiry_returns_false(self):
        # 2026-08-03 is a Monday — no expiry on Monday
        dt = datetime(2026, 8, 3, 15, 0, 0)
        assert is_expiry_day(dt) is False

    def test_tuesday_not_in_set_triggers_fallback(self, caplog):
        """
        A Tuesday that's not in the calendar should still return True
        (fallback) but emit a WARNING.
        """
        # Find a Tuesday not in our set (far future)
        future_tuesday = date(2030, 1, 1)  # 2030-01-01 is a Tuesday
        assert future_tuesday.weekday() == 1  # sanity check
        assert future_tuesday not in NIFTY_EXPIRY_DATES

        with caplog.at_level(logging.WARNING, logger="kavach.risk.expiry_calendar"):
            result = is_expiry_day(datetime.combine(future_tuesday, datetime.min.time()))

        assert result is True
        assert "Tuesday fallback" in caplog.text

    def test_known_expiry_set_contains_only_tuesdays_after_sep_2025(self):
        """All dates from Sep 2025 onwards must be Tuesdays (weekday == 1)."""
        cutoff = date(2025, 9, 1)
        non_tuesdays = [
            d for d in NIFTY_EXPIRY_DATES
            if d >= cutoff and d.weekday() != 1
        ]
        assert non_tuesdays == [], (
            f"Found non-Tuesday expiry dates after Sep 2025: {non_tuesdays}"
        )

    def test_date_object_input(self):
        """is_expiry_day must accept datetime objects (not bare date)."""
        dt = datetime(2026, 9, 1, 9, 15)
        assert is_expiry_day(dt) is True
