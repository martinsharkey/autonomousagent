#!/usr/bin/env python3
"""Test Telegram integration."""

import asyncio
from core.telegram import get_telegram_bot, send_telegram_message

async def test_telegram():
    """Test sending a Telegram message."""
    print("Testing Telegram integration...")
    
    bot = get_telegram_bot()
    
    if not bot.bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        return False
    
    if not bot.chat_id:
        print("ERROR: TELEGRAM_CHAT_ID not set in .env")
        return False
    
    print(f"Bot token: {bot.bot_token[:20]}...")
    print(f"Chat ID: {bot.chat_id}")
    
    # Send test message
    success = await send_telegram_message(
        "<b>🤖 Telegram Integration Test</b>\n\n"
        "The Autonomous 3-Agent Council is now fully operational!\n\n"
        "<b>Status:</b> ✅ All systems go\n"
        "<b>Models:</b>\n"
        "  • Orchestrator: Qwen3.5:4b\n"
        "  • Evaluator: Phi-4 Mini\n"
        "  • Worker: DeepSeek Coder 1.3B\n\n"
        "<i>Integration test successful!</i>"
    )
    
    if success:
        print("✅ Telegram message sent successfully!")
        return True
    else:
        print("❌ Failed to send Telegram message")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_telegram())
    exit(0 if result else 1)
