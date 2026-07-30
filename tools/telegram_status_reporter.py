import json
import os
from datetime import datetime

class TelegramStatusReporter:
    """Generates and sends human-readable status reports to Telegram."""

    def __init__(self, telegram_bot=None):
        self.bot = telegram_bot

    def generate_report(self, recent_actions: list, success_rate: float, resource_usage: dict) -> str:
        """Create a concise natural language status summary."""
        lines = [f"*Autobot Status Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*"]
        lines.append(f"\n*Recent Actions:* {len(recent_actions)} actions in last period")
        if recent_actions:
            lines.append(f"Latest: {recent_actions[-1][:100]}")
        lines.append(f"\n*Success Rate:* {success_rate*100:.1f}%")
        lines.append(f"*Resource Usage:* {json.dumps(resource_usage, indent=2)}")
        return "\n".join(lines)

    async def send_report(self, chat_id: str, report: str):
        """Send the report via Telegram bot if available."""
        if self.bot:
            await self.bot.send_message(chat_id=chat_id, text=report, parse_mode='Markdown')
        else:
            # Fallback: log to file
            log_path = "session_log.md"
            with open(log_path, "a") as f:
                f.write(f"\n\n## Status Report - {datetime.utcnow().isoformat()}\n{report}\n")
