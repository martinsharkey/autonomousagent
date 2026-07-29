#!/usr/bin/env python3
"""Companion Reporter: sends natural-language status summaries to Telegram."""
import json
import os
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram_message(text: str) -> bool:
    """Send a plain text message to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False

def build_status_summary(success_rate: float, recent_actions: list, resource_usage: dict) -> str:
    """Build a human-readable status summary."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"*Autobot Status Report* — {now}",
        "",
        f"*Success Rate:* {success_rate*100:.1f}%",
        f"*Recent Actions:* {len(recent_actions)} actions in last window",
        f"*Resource Usage:* {resource_usage.get('api_calls', 0)} API calls, {resource_usage.get('tokens_used', 0)} tokens",
        "",
        "*Recent Activity:*"
    ]
    for action in recent_actions[-5:]:
        lines.append(f"- {action.get('tool', 'unknown')}: {action.get('status', 'done')}")
    return "\n".join(lines)

def report_status(success_rate: float = 0.0, recent_actions: list = None, resource_usage: dict = None):
    """Main entry point: build and send status summary."""
    if recent_actions is None:
        recent_actions = []
    if resource_usage is None:
        resource_usage = {}
    summary = build_status_summary(success_rate, recent_actions, resource_usage)
    ok = send_telegram_message(summary)
    return {"sent": ok, "summary_length": len(summary)}

if __name__ == "__main__":
    # Example usage
    result = report_status(
        success_rate=0.85,
        recent_actions=[
            {"tool": "code_validator", "status": "passed"},
            {"tool": "provider_optimizer", "status": "switched provider"}
        ],
        resource_usage={"api_calls": 42, "tokens_used": 15000}
    )
    print(json.dumps(result))
