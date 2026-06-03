"""Channel-agnostic core of the bot: conversation memory, persona, the LLM call,
and human-like send timing. Both the SMS webhook (app.py) and the Telegram poller
(run_telegram.py) feed messages through process_message()."""

import os
import time
import random
import logging
import threading
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from groq import Groq

from config import (
    SYSTEM_PROMPT, GROQ_MODEL, MAX_TOKENS,
    TYPING_SPEED_WPM, TYPING_JITTER_FRACTION, TYPING_DELAY_MIN, TYPING_DELAY_MAX,
    BUSY_DELAY_CHANCE, BUSY_DELAY_MIN, BUSY_DELAY_MAX,
    AUTO_UPDATE_CONTACTS, LOGS_DIR,
)
from conversation import ConversationHistory
from channels.base import Messenger
import profiles

# ─── Logging ──────────────────────────────────────────────────────────────────
os.makedirs(LOGS_DIR, exist_ok=True)
log = logging.getLogger("smsbot")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

_file_handler = TimedRotatingFileHandler(
    os.path.join(LOGS_DIR, "chat.log"),
    when="midnight",
    backupCount=30,
    encoding="utf-8",
)
_file_handler.suffix = "%Y-%m-%d"
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

if not log.handlers:
    log.addHandler(_file_handler)
    log.addHandler(_console_handler)

# ─── Shared state ───────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
history = ConversationHistory()

BOT_PERSONA = profiles.load_persona() or SYSTEM_PROMPT
log.info(f"[PERSONA] Loaded: {BOT_PERSONA[:80]}{'...' if len(BOT_PERSONA) > 80 else ''}")


def _build_system_content(sender_id: str) -> str:
    contact = profiles.load_contact(sender_id)
    content = BOT_PERSONA
    if contact:
        content += f"\n\nWhat you know about this person:\n{contact}"
    content += f"\n\nCurrent date and time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}"
    return content


def _send_and_update(messenger: Messenger, to: str, message: str, delay: float,
                     user_message: str, ai_reply: str) -> None:
    time.sleep(delay)
    messenger.send(to, message)
    if AUTO_UPDATE_CONTACTS and user_message:
        profiles.update_contact(to, user_message, ai_reply, groq_client)


def process_message(messenger: Messenger, sender_id: str, user_message: str) -> None:
    """Handle one inbound message from any channel and reply via `messenger`."""
    user_message = (user_message or "").strip()
    if not user_message:
        return

    if user_message.lower() == "reset":
        history.clear(sender_id)
        log.info(f"[RESET] {sender_id}")
        threading.Thread(
            target=_send_and_update,
            args=(messenger, sender_id, "Conversation cleared. Starting fresh!", TYPING_DELAY_MIN, "", ""),
            daemon=True,
        ).start()
        return

    log.info(f"[IN]   {sender_id}: {user_message}")
    history.add(sender_id, "user", user_message)

    system_content = _build_system_content(sender_id)
    messages = [{"role": "system", "content": system_content}] + history.get(sender_id)

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
        )
        ai_reply = completion.choices[0].message.content or "Sorry, I couldn't come up with a response."
        history.add(sender_id, "assistant", ai_reply)
    except Exception as e:
        log.error(f"[ERR]  Groq error for {sender_id}: {e}")
        ai_reply = "Sorry, I'm having trouble right now. Try again in a moment."
        history.add(sender_id, "assistant", ai_reply)
        user_message = ""

    word_count = len(ai_reply.split())
    delay = (word_count / TYPING_SPEED_WPM) * 60
    jitter = delay * TYPING_JITTER_FRACTION * random.uniform(-1, 1)
    delay = max(TYPING_DELAY_MIN, min(TYPING_DELAY_MAX, delay + jitter))
    if random.random() < BUSY_DELAY_CHANCE:
        busy_extra = random.uniform(BUSY_DELAY_MIN, BUSY_DELAY_MAX)
        delay += busy_extra
        log.info(f"[BUSY] {sender_id} adding {busy_extra:.0f}s busy delay")
    log.info(f"[OUT]  {sender_id} in {delay:.1f}s: {ai_reply}")

    # Send after delay in background; also runs contact auto-update after sending.
    threading.Thread(
        target=_send_and_update,
        args=(messenger, sender_id, ai_reply, delay, user_message, ai_reply),
        daemon=True,
    ).start()
