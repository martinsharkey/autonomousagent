import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from core.telegram import TELEGRAM_TOKEN, CHAT_ID


async def send_telegram_message(text: str) -> bool:
    """Send a plain text message to the configured Telegram chat."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
        except Exception:
            return False


def format_status_report(
    success_rate: float,
    recent_decisions: list[str],
    pending_mutations: list[str],
    last_evolution: Optional[str] = None,
) -> str:
    """Format a human-readable status report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"*Autobot Status Report* — {now}",
        "",
        f"*Success Rate:* {success_rate:.1%}",
        "",
        "*Recent Decisions:*",
    ]
    if recent_decisions:
        for d in recent_decisions[-5:]:
            lines.append(f"- {d}")
    else:
        lines.append("- No recent decisions")
    lines.append("")
    lines.append("*Pending Mutations:*")
    if pending_mutations:
        for m in pending_mutations[-5:]:
            lines.append(f"- {m}")
    else:
        lines.append("- None")
    if last_evolution:
        lines.append("")
        lines.append(f"*Last Evolution:* {last_evolution}")
    return "\n".join(lines)


async def report_status(
    success_rate: float = 0.0,
    recent_decisions: Optional[list[str]] = None,
    pending_mutations: Optional[list[str]] = None,
    last_evolution: Optional[str] = None,
) -> dict:
    """Send a status report to the human council via Telegram.

    Args:
        success_rate: Recent success rate (0.0 to 1.0)
        recent_decisions: List of recent decision summaries
        pending_mutations: List of pending mutation descriptions
        last_evolution: Description of the last evolution

    Returns:
        dict with 'success' bool and optional 'error' string
    """
    if recent_decisions is None:
        recent_decisions = []
    if pending_mutations is None:
        pending_mutations = []

    message = format_status_report(
        success_rate=success_rate,
        recent_decisions=recent_decisions,
        pending_mutations=pending_mutations,
        last_evolution=last_evolution,
    )
    ok = await send_telegram_message(message)
    if ok:
        return {"success": True}
    else:
        return {"success": False, "error": "Failed to send Telegram message"}


if __name__ == "__main__":
    # Example usage
    asyncio.run(report_status(
        success_rate=0.75,
        recent_decisions=["Approved mutation X", "Rejected mutation Y"],
        pending_mutations=["Add new tool Z", "Optimize prompt A"],
        last_evolution="Improved feedback loop",
    ))
