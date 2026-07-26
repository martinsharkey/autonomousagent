from dotenv import load_dotenv
import os

print("Before load_dotenv:")
print(f"  HMAC_SECRET_KEY: {os.getenv('HMAC_SECRET_KEY', 'NOT SET')}")

load_dotenv()

print("\nAfter load_dotenv:")
print(f"  HMAC_SECRET_KEY: {os.getenv('HMAC_SECRET_KEY', 'NOT SET')}")
print(f"  TELEGRAM_BOT_TOKEN: {bool(os.getenv('TELEGRAM_BOT_TOKEN'))}")
print(f"  TELEGRAM_CHAT_ID: {os.getenv('TELEGRAM_CHAT_ID', 'NOT SET')}")
