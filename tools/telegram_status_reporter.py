import asyncio
import json
import os
from datetime import datetime
from typing import Optional

import aiohttp

from core.health import get_health_status
from core.feedback import get_recent_feedback
from core.goals import get_active_goals

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
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

def build_status_report() -> str:
    """Build a natural language status report."""
    health = get_health_status()
    feedback = get_recent_feedback(limit=3)
    goals = get_active_goals()
    now = datetime.utcnow().isoformat()
    
    lines = [
        f"*Agent Status Report* - {now}",
        "",
        "*Health:*",
        f"- Uptime: {health.get('uptime_hours', 'N/A')} hours",
        f"- Memory usage: {health.get('memory_percent', 'N/A')}%",
        f"- Last error: {health.get('last_error', 'None')}",
        "",
        "*Recent Feedback:*",
    ]
    if feedback:
        for fb in feedback:
            lines.append(f"- {fb.get('summary', 'No summary')}")
    else:
        lines.append("- No recent feedback")
    
    lines.append("")
    lines.append("*Active Goals:*")
    if goals:
        for g in goals:
            lines.append(f"- {g.get('description', 'No description')} (progress: {g.get('progress', 0)}%)")
    else:
        lines.append("- No active goals")
    
    return "\n".join(lines)

async def report_status() -> dict:
    """Main entry point: build and send status report."""
    report = build_status_report()
    success = await send_telegram_message(report)
    return {
        "success": success,
        "report_length": len(report),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    asyncio.run(report_status())
