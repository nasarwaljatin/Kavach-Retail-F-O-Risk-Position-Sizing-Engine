"""
Tests for the Telegram alert dispatcher.
httpx.post is mocked — no real network calls.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.alerts import send_telegram_alert, format_risk_alert


class TestSendTelegramAlert:
    def test_no_op_when_token_empty(self):
        """Should return False silently when token not configured."""
        with patch("app.core.alerts.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = ""
            mock_settings.TELEGRAM_CHAT_ID = "123"
            result = send_telegram_alert("test message")
        assert result is False

    def test_no_op_when_chat_id_empty(self):
        with patch("app.core.alerts.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "abc:token"
            mock_settings.TELEGRAM_CHAT_ID = ""
            result = send_telegram_alert("test message")
        assert result is False

    def test_sends_post_when_configured(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("app.core.alerts.settings") as mock_settings, \
             patch("app.core.alerts.httpx.post", return_value=mock_resp) as mock_post:
            mock_settings.TELEGRAM_BOT_TOKEN = "123456:TestToken"
            mock_settings.TELEGRAM_CHAT_ID = "-1001234567890"
            result = send_telegram_alert("Hello from Kavach")

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs["json"]
        assert "Hello from Kavach" in str(payload)

    def test_returns_false_on_non_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"

        with patch("app.core.alerts.settings") as mock_settings, \
             patch("app.core.alerts.httpx.post", return_value=mock_resp):
            mock_settings.TELEGRAM_BOT_TOKEN = "123456:TestToken"
            mock_settings.TELEGRAM_CHAT_ID = "99999"
            result = send_telegram_alert("test")

        assert result is False

    def test_returns_false_on_exception(self):
        with patch("app.core.alerts.settings") as mock_settings, \
             patch("app.core.alerts.httpx.post", side_effect=Exception("network error")):
            mock_settings.TELEGRAM_BOT_TOKEN = "123456:TestToken"
            mock_settings.TELEGRAM_CHAT_ID = "99999"
            result = send_telegram_alert("test")

        assert result is False


class TestFormatRiskAlert:
    def test_contains_key_fields(self):
        msg = format_risk_alert(
            action_taken="squared_off",
            triggered_breakers=["DAILY_LOSS_LIMIT", "MARGIN_CAP"],
            day_pnl=-2500.0,
            capital_base=100000.0,
            paper_mode=True,
        )
        assert "SQUARED OFF" in msg
        assert "DAILY_LOSS_LIMIT" in msg
        assert "PAPER" in msg
        assert "-2,500.00" in msg or "2500" in msg

    def test_alert_mode(self):
        msg = format_risk_alert(
            action_taken="alert",
            triggered_breakers=["ORDER_VELOCITY_REVENGE_TRADING"],
            day_pnl=500.0,
            capital_base=100000.0,
            paper_mode=False,
        )
        assert "ALERT" in msg
        assert "LIVE" in msg or "PAPER" not in msg

    def test_paper_mode_tag(self):
        msg_paper = format_risk_alert("alert", [], 0, 100000, paper_mode=True)
        msg_live = format_risk_alert("alert", [], 0, 100000, paper_mode=False)
        assert "PAPER" in msg_paper
        assert "LIVE" in msg_live
