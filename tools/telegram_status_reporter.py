import asyncio
import json
import os
from datetime import datetime
from typing import Optional

import httpx

from core.health import get_health_status
from core.goals import get_all_goals
from core.agent_config import get_current_config

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

async def send_telegram_message(text: str) -> bool:
    """Send a plain text message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
        except Exception:
            return False

def format_status_report() -> str:
    """Generate a natural language status summary."""
    health = get_health_status()
    goals = get_all_goals()
    config = get_current_config()

    lines = []
    lines.append("*Agent Status Report*")
    lines.append(f"Time: {datetime.utcnow().isoformat()}Z")
    lines.append("")
    lines.append("*Health:*")
    if health:
        for key, value in health.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No health data available.")
    lines.append("")
    lines.append("*Active Goals:*")
    if goals:
        for g in goals[:5]:
            status = g.get("status", "unknown")
            desc = g.get("description", "No description")
            lines.append(f"- [{status}] {desc}")
    else:
        lines.append("- No goals set.")
    lines.append("")
    lines.append("*Configuration:*")
    if config:
        lines.append(f"- Model: {config.get('model', 'unknown')}")
        lines.append(f"- Provider: {config.get('provider', 'unknown')}")
    else:
        lines.append("- No config loaded.")
    return "\n".join(lines)

async def report_status() -> dict:
    """Main entry point: generate and send status report."""
    report = format_status_report()
    success = await send_telegram_message(report)
    return {
        "success": success,
        "message": "Status report sent." if success else "Failed to send status report.",
        "report_length": len(report)
    }

if __name__ == "__main__":
    asyncio.run(report_status())
