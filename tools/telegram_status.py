#!/usr/bin/env python3
"""Telegram status reporter - sends periodic natural-language summaries to a configured chat."""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Configurable via environment or config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_message(text: str) -> bool:
    """Send a plain text message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured; skipping message.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram message sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def build_status_report(
    health_data: Optional[dict] = None,
    mutation_count: int = 0,
    council_activity: Optional[str] = None,
    recent_errors: Optional[list] = None
) -> str:
    """Build a natural-language status report from available data."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"*Autobot Status Report* — {now}",
        "",
    ]
    if health_data:
        lines.append("*Health:*")
        for key, value in health_data.items():
            lines.append(f"  • {key}: {value}")
        lines.append("")
    lines.append(f"*Mutations proposed:* {mutation_count}")
    if council_activity:
        lines.append(f"*Council:* {council_activity}")
    if recent_errors:
        lines.append(f"*Recent errors ({len(recent_errors)}):*")
        for err in recent_errors[-3:]:
            lines.append(f"  • {err}")
    return "\n".join(lines)


def send_status_report(
    health_data: Optional[dict] = None,
    mutation_count: int = 0,
    council_activity: Optional[str] = None,
    recent_errors: Optional[list] = None
) -> bool:
    """Build and send a status report via Telegram."""
    report = build_status_report(health_data, mutation_count, council_activity, recent_errors)
    return send_telegram_message(report)


if __name__ == "__main__":
    # Example usage
    send_status_report(
        health_data={"status": "ok", "uptime_hours": 12},
        mutation_count=5,
        council_activity="3 votes cast, 1 mutation promoted",
        recent_errors=["Timeout on provider X", "Rate limit hit"]
    )
