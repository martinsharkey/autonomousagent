import os
import asyncio
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()


class TelegramBot:
    """Telegram bot for council communication and notifications."""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.bot: Optional[Bot] = None
        
        if self.bot_token:
            self.bot = Bot(token=self.bot_token)
    
    async def send_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """Send a message to the specified chat."""
        if not self.bot:
            print("[TELEGRAM] Bot not initialized - missing TELEGRAM_BOT_TOKEN")
            return False
        
        target_chat_id = chat_id or self.chat_id
        if not target_chat_id:
            print("[TELEGRAM] No chat_id provided")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=target_chat_id,
                text=message,
                parse_mode="HTML"
            )
            print(f"[TELEGRAM] Message sent to {target_chat_id}")
            return True
        except TelegramError as e:
            print(f"[TELEGRAM] Error sending message: {e}")
            return False
    
    async def send_council_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Send a formatted council status message."""
        message = f"<b>🤖 Council Status Update</b>\n\n"
        message += f"<b>Status:</b> {status}\n"
        
        if details:
            message += "\n<b>Details:</b>\n"
            for key, value in details.items():
                message += f"  • {key}: {value}\n"
        
        return await self.send_message(message)
    
    async def send_completion_notification(self, session_id: str, summary: Dict[str, Any]) -> bool:
        """Send a completion notification when council finishes."""
        message = f"<b>✅ Council Task Complete</b>\n\n"
        message += f"<b>Session:</b> {session_id}\n"
        message += f"<b>Loop Count:</b> {summary.get('loop_count', 'N/A')}\n"
        message += f"<b>Completed Nodes:</b> {', '.join(summary.get('completed_nodes', []))}\n"
        
        if 'messages_count' in summary:
            message += f"<b>Messages:</b> {summary['messages_count']}\n"
        
        message += "\n<i>The council has completed its task successfully.</i>"
        
        return await self.send_message(message)
    
    async def send_error_notification(self, error: str, context: Optional[str] = None) -> bool:
        """Send an error notification."""
        message = f"<b>❌ Council Error</b>\n\n"
        message += f"<b>Error:</b> {error}\n"
        
        if context:
            message += f"\n<b>Context:</b> {context}\n"
        
        return await self.send_message(message)


# Global bot instance
_telegram_bot: Optional[TelegramBot] = None


def get_telegram_bot() -> TelegramBot:
    """Get or create the global Telegram bot instance."""
    global _telegram_bot
    if _telegram_bot is None:
        _telegram_bot = TelegramBot()
    return _telegram_bot


async def send_telegram_message(message: str, chat_id: Optional[str] = None) -> bool:
    """Convenience function to send a Telegram message."""
    bot = get_telegram_bot()
    return await bot.send_message(message, chat_id)


async def notify_council_completion(session_id: str, summary: Dict[str, Any]) -> bool:
    """Notify via Telegram that the council has completed."""
    bot = get_telegram_bot()
    return await bot.send_completion_notification(session_id, summary)


async def notify_council_error(error: str, context: Optional[str] = None) -> bool:
    """Notify via Telegram that an error occurred."""
    bot = get_telegram_bot()
    return await bot.send_error_notification(error, context)
