#!/usr/bin/env python3
"""Run the bot on Telegram via long-polling (no phone number, no public webhook).

Run alongside the SMS Flask app as its own process:  python run_telegram.py
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Imported after load_dotenv() — brain reads env vars at import time.
from config import ENABLE_TELEGRAM, TELEGRAM_ALLOWED_CHAT_IDS
from channels.telegram import TelegramMessenger
import brain

log = logging.getLogger("smsbot")


def main():
    if not ENABLE_TELEGRAM:
        raise SystemExit("Telegram is disabled (set ENABLE_TELEGRAM = True in config.py)")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set — add it to .env (get one from @BotFather)")

    messenger = TelegramMessenger(token)
    me = messenger.get_me()
    if not me.get("ok"):
        raise SystemExit(f"Telegram auth failed: {me.get('description')}")
    log.info(f"[TELEGRAM] Connected as @{me['result'].get('username')}")

    def handler(chat_id: str, text: str) -> None:
        if TELEGRAM_ALLOWED_CHAT_IDS and chat_id not in TELEGRAM_ALLOWED_CHAT_IDS:
            return
        brain.process_message(messenger, chat_id, text)

    messenger.poll(handler)


if __name__ == "__main__":
    main()
