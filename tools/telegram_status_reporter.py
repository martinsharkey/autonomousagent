import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional

# Assume telegram bot token and chat id are configured via environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(text: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not configured; skipping message.")
        return False
    try:
        import aiohttp
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    return True
                else:
                    print(f"Telegram API error: {resp.status} {await resp.text()}")
                    return False
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def get_recent_health_summary() -> str:
    """Fetch health status from core.health if available."""
    try:
        from core.health import get_health_status
        health = get_health_status()
        if health:
            return f"Health: {health.get('status', 'unknown')} (uptime: {health.get('uptime_seconds', '?')}s)"
    except Exception as e:
        print(f"Health summary unavailable: {e}")
    return "Health: unknown"

def get_recent_actions() -> str:
    """Read recent actions from session_log.md or audit log."""
    try:
        # Try to read last few lines of session_log.md
        with open("session_log.md", "r") as f:
            lines = f.readlines()
        recent = lines[-5:]
        if recent:
            return "Recent actions:\n" + "".join(recent)
    except Exception as e:
        print(f"Could not read session log: {e}")
    return "Recent actions: none"

def get_pending_goals() -> str:
    """Fetch pending goals from core.goals if available."""
    try:
        from core.goals import get_pending_goals
        goals = get_pending_goals()
        if goals:
            goal_list = "\n".join([f"- {g.get('description', '?')}" for g in goals[:5]])
            return f"Pending goals:\n{goal_list}"
    except Exception as e:
        print(f"Goals unavailable: {e}")
    return "Pending goals: none"

def compose_status_message() -> str:
    """Compose a natural-language status update."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"*Agent Status Update* ({timestamp})",
        get_recent_health_summary(),
        get_recent_actions(),
        get_pending_goals()
    ]
    return "\n\n".join(lines)

async def report_status(force: bool = False) -> dict:
    """Send a status report to Telegram. If force is False, only send if there are notable changes (simplified: always send for now)."""
    message = compose_status_message()
    success = await send_telegram_message(message)
    return {"success": success, "message": message}

if __name__ == "__main__":
    asyncio.run(report_status(force=True))
