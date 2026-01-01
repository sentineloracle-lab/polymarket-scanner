import os

SCANNER_MODE = "aggressive"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
