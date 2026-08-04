#!/usr/bin/env python3
"""
Kavach Telegram Bot Setup Helper
==================================
Run this AFTER you've created a bot via @BotFather and have your token.

Usage:
    python scripts/setup_telegram.py

The script will:
  1. Prompt you to paste the bot token
  2. Open t.me/<botname> instructions for you to get the chat_id
  3. Send a test message to verify everything works
  4. Write TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to ../.env

Steps to create the bot (do these in Telegram first):
  1. Open Telegram and search for  @BotFather
  2. Send:  /newbot
  3. Choose a name:  Kavach Risk Alert
  4. Choose a username:  kavach_risk_YOURNAME_bot  (must end in _bot)
  5. BotFather will give you the token: 123456789:ABCxyz...
  6. To get your chat_id:
       - Add the bot to a group OR send it a /start DM
       - Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
       - Look for  "chat": {"id": -123456789}  in the JSON
"""

import json
import os
import re
import sys
from pathlib import Path

import httpx

# Allow running from scripts/ dir or repo root
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT.parent / ".env"   # project root .env (one level above backend/)

# Force UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def _green(text: str) -> str:
    return f"\033[92m{text}\033[0m"


def _red(text: str) -> str:
    return f"\033[91m{text}\033[0m"


def _yellow(text: str) -> str:
    return f"\033[93m{text}\033[0m"


def validate_token(token: str) -> bool:
    """Check token format: NNN:AAAA (digits colon at least 10 chars)."""
    return bool(re.match(r"^\d+:[A-Za-z0-9_-]{10,}$", token))


def get_chat_id_from_updates(token: str) -> str | None:
    """Try to auto-detect chat_id from recent /getUpdates."""
    try:
        resp = httpx.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            timeout=5.0,
        )
        data = resp.json()
        results = data.get("result", [])
        for update in reversed(results):
            chat = (
                update.get("message", {}).get("chat")
                or update.get("my_chat_member", {}).get("chat")
            )
            if chat:
                return str(chat["id"])
    except Exception:
        pass
    return None


def send_test_message(token: str, chat_id: str) -> bool:
    """Send a test message. Returns True on success."""
    msg = (
        "*Kavach Risk Engine* — bot connected successfully! \U0001F6E1\n"
        "You will receive circuit breaker alerts here."
    )
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=5.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


def write_to_env(token: str, chat_id: str) -> None:
    """Upsert TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in root .env file."""
    env_path = _ENV_FILE

    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
    else:
        content = ""

    def _upsert(text: str, key: str, value: str) -> str:
        pattern = rf"^{re.escape(key)}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, text, re.MULTILINE):
            return re.sub(pattern, replacement, text, flags=re.MULTILINE)
        else:
            sep = "\n" if text and not text.endswith("\n") else ""
            return text + sep + replacement + "\n"

    content = _upsert(content, "TELEGRAM_BOT_TOKEN", token)
    content = _upsert(content, "TELEGRAM_CHAT_ID", chat_id)
    env_path.write_text(content, encoding="utf-8")
    print(_green(f"  Written to: {env_path}"))


def main() -> None:
    print()
    print(_bold("=" * 56))
    print(_bold("  Kavach — Telegram Bot Setup"))
    print(_bold("=" * 56))
    print()
    print("Before running this, complete these steps in Telegram:")
    print("  1. Search for @BotFather and send: /newbot")
    print("  2. Name: Kavach Risk Alert")
    print("  3. Username: kavach_risk_YOURNAME_bot")
    print("  4. Copy the token BotFather gives you")
    print()

    # --- Token ---
    token = input("Paste your bot token here: ").strip()
    if not validate_token(token):
        print(_red("  Invalid token format. Expected: 123456789:ABCxyz..."))
        sys.exit(1)
    print(_green("  Token format OK."))
    print()

    # --- Auto-detect chat_id ---
    print("Attempting to auto-detect your chat_id from recent messages...")
    print(_yellow("  (If this fails, open: "
                  f"https://api.telegram.org/bot{token}/getUpdates )"))
    print()

    chat_id = get_chat_id_from_updates(token)

    if chat_id:
        print(_green(f"  Auto-detected chat_id: {chat_id}"))
    else:
        print(_yellow("  Could not auto-detect. Trying to get it manually..."))
        print()
        print("  1. Send your bot a message (or add it to a group)")
        print(f"  2. Open: https://api.telegram.org/bot{token}/getUpdates")
        print("  3. Find  \"chat\": {\"id\": ...}  in the JSON")
        print()
        chat_id = input("Paste your chat_id here: ").strip()

    if not chat_id:
        print(_red("  No chat_id provided. Aborting."))
        sys.exit(1)

    # --- Test message ---
    print()
    print("Sending test message...")
    if send_test_message(token, chat_id):
        print(_green("  Test message sent successfully! Check Telegram."))
    else:
        print(_red("  Failed to send test message. Check token and chat_id."))
        sys.exit(1)

    # --- Write to .env ---
    print()
    print(f"Writing to .env ({_ENV_FILE})...")
    write_to_env(token, chat_id)

    print()
    print(_bold(_green("  Setup complete!")))
    print()
    print("Next steps:")
    print("  - Redeploy to Render and set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID")
    print("    in Render's Environment Variables panel")
    print("  - Or restart the local backend: uvicorn app.main:app --reload")
    print()


if __name__ == "__main__":
    main()
