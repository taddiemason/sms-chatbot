# ─── AI Behavior ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a friendly and helpful assistant communicating over SMS.
Keep replies concise and clear — SMS has limited space.
Never use markdown formatting like ** or # since it won't render in SMS."""

# Groq model to use. Other options: "llama-3.1-8b-instant", "mixtral-8x7b-32768"
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 300

PERSONA_FILE = "persona.txt"
CONTACTS_DIR = "contacts"
AUTO_UPDATE_CONTACTS = True
LOGS_DIR = "logs"

# ─── Context Window ────────────────────────────────────────────────────────────
# How many past messages (user + assistant combined) to keep per sender.
# Higher = more memory, more tokens used per request.
MAX_HISTORY_MESSAGES = 20
CONVERSATION_EXPIRY_HOURS = 24

# ─── Channels ──────────────────────────────────────────────────────────────────
# SMS is served by app.py (Vonage webhook). Telegram is served by run_telegram.py
# (long-polling). Each runs as its own process; toggle Telegram here.
ENABLE_TELEGRAM = True

# ─── Number Filter (SMS) ─────────────────────────────────────────────────────────
# Leave empty to respond to everyone, or add numbers in E.164 format to whitelist.
ALLOWED_NUMBERS = set()

# ─── Chat ID Filter (Telegram) ───────────────────────────────────────────────────
# Leave empty to respond to everyone, or add Telegram chat IDs (as strings) to
# whitelist, e.g. {"123456789"}. A user's chat ID is logged on their first message.
TELEGRAM_ALLOWED_CHAT_IDS = set()

# ─── Typing Delay ──────────────────────────────────────────────────────────────
# Simulates a human typing the reply before sending.
# Delay is calculated from word count at TYPING_SPEED_WPM, then a random jitter
# of ±TYPING_JITTER_FRACTION is applied (e.g. 0.3 = ±30%).
TYPING_SPEED_WPM = 40          # words per minute (average human: 38-45)
TYPING_JITTER_FRACTION = 0.3   # randomness factor
TYPING_DELAY_MIN = 1.0         # minimum seconds before replying
TYPING_DELAY_MAX = 15.0        # cap so long messages don't stall too long

# ─── Busy Delay ────────────────────────────────────────────────────────────────
# Occasionally adds a longer "got busy" pause before the bot replies.
# BUSY_DELAY_CHANCE = probability per message (0.0 = never, 1.0 = always).
# When triggered, a random extra delay between MIN and MAX seconds is added
# on top of the normal typing delay.
BUSY_DELAY_CHANCE = 0.25       # 25% chance per message
BUSY_DELAY_MIN = 60.0          # 1 minute
BUSY_DELAY_MAX = 600.0         # 10 minutes
