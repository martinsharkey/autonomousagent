import json
import requests
from typing import Optional

TELEGRAM_BOT_TOKEN_KEY = "TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID_KEY = "TELEGRAM_CHAT_ID"

def telegram_status_report(
    message: str,
    parse_mode: Optional[str] = "Markdown",
    disable_notification: bool = False
) -> dict:
    """
    Send a formatted status update to the human companion via Telegram.

    Args:
        message: The text message to send. Supports Markdown formatting.
        parse_mode: 'Markdown' or 'HTML' for formatting. Default 'Markdown'.
        disable_notification: If True, sends silently.

    Returns:
        dict with 'success' bool and optional 'error' string.
    """
    try:
        from core.telegram import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    except ImportError:
        return {"success": False, "error": "Telegram config not available"}

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"success": False, "error": "Telegram credentials not configured"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return {"success": True}
        else:
            return {"success": False, "error": f"Telegram API error: {resp.status_code} - {resp.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
