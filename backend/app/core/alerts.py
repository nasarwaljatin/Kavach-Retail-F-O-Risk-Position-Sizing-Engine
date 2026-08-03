"""
Telegram alert dispatcher for Kavach risk events.

Sends a message to a Telegram chat when a circuit breaker fires.
No-op (returns False) when TELEGRAM_BOT_TOKEN is not configured
— never raises, never crashes the monitor loop.

Setup:
  1. Create a bot via @BotFather, copy the token.
  2. Add the bot to a group / channel, get the chat_id.
  3. Set in .env:
       TELEGRAM_BOT_TOKEN=123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
       TELEGRAM_CHAT_ID=-1001234567890   (group) or 123456 (user)
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("kavach.core.alerts")

_TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_alert(message: str, parse_mode: str = "Markdown") -> bool:
    """
    POST a message to the configured Telegram chat.

    Returns True on success, False otherwise.
    Safe to call even when tokens are not configured — returns False silently.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.debug(
            "Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set."
        )
        return False

    url = _TELEGRAM_API_BASE.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }

    try:
        resp = httpx.post(url, json=payload, timeout=5.0)
        if resp.status_code == 200:
            logger.info("Telegram alert sent successfully.")
            return True
        else:
            logger.warning(
                "Telegram API returned status %d: %s", resp.status_code, resp.text
            )
            return False
    except Exception as exc:
        logger.error("Failed to send Telegram alert: %s", exc)
        return False


def format_risk_alert(
    action_taken: str,
    triggered_breakers: list,
    day_pnl: float,
    capital_base: float,
    paper_mode: bool,
) -> str:
    """
    Format a concise Markdown alert message for a risk event.
    """
    mode_tag = "📄 PAPER" if paper_mode else "🔴 LIVE"
    pnl_sign = "+" if day_pnl >= 0 else ""
    breakers_str = ", ".join(triggered_breakers) if triggered_breakers else "none"

    action_emoji = {
        "squared_off": "🛑 SQUARED OFF",
        "alert": "⚠️ ALERT",
        "blocked": "🚫 BLOCKED",
    }.get(action_taken, action_taken.upper())

    return (
        f"*Kavach Risk Engine* {mode_tag}\n"
        f"Action: *{action_emoji}*\n"
        f"Breakers: `{breakers_str}`\n"
        f"Day P\\&L: `₹{pnl_sign}{day_pnl:,.2f}` "
        f"({pnl_sign}{(day_pnl / capital_base * 100) if capital_base else 0:.2f}%)\n"
    )
