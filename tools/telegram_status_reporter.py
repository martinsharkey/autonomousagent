import os
import json
import requests
from typing import Optional

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram_message(text: str) -> bool:
    """Send a plain text message to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False

def report_status(status_data: dict) -> dict:
    """
    Format and send a status report to the human companion.
    Expected keys: agent_name, success_rate, recent_actions, health_status, pending_decisions
    """
    lines = []
    lines.append(f"*Status Report from {status_data.get('agent_name', 'Unknown')}*")
    lines.append(f"Success Rate: {status_data.get('success_rate', 'N/A')}")
    lines.append(f"Health: {status_data.get('health_status', 'Unknown')}")
    actions = status_data.get('recent_actions', [])
    if actions:
        lines.append("Recent Actions:")
        for a in actions[-5:]:
            lines.append(f"- {a}")
    decisions = status_data.get('pending_decisions', [])
    if decisions:
        lines.append("Pending Decisions:")
        for d in decisions:
            lines.append(f"- {d}")
    message = "\n".join(lines)
    success = send_telegram_message(message)
    return {"sent": success, "message_length": len(message)}

def report_decision(decision: str, context: Optional[str] = None) -> dict:
    """Send a decision notification to the companion."""
    text = f"*Decision Made:* {decision}"
    if context:
        text += f"\nContext: {context}"
    success = send_telegram_message(text)
    return {"sent": success}

def report_error(error_message: str) -> dict:
    """Send an error alert to the companion."""
    text = f"*Error Alert:* {error_message}"
    success = send_telegram_message(text)
    return {"sent": success}
