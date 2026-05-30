# ─── AI Behavior ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a friendly and helpful assistant communicating over SMS.
Keep replies concise and clear — SMS has limited space.
Never use markdown formatting like ** or # since it won't render in SMS."""

# Groq model to use. Other options: "llama-3.1-8b-instant", "mixtral-8x7b-32768"
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 300

# ─── Context Window ────────────────────────────────────────────────────────────
# How many past messages (user + assistant combined) to keep per sender.
# Higher = more memory, more tokens used per request.
MAX_HISTORY_MESSAGES = 20
CONVERSATION_EXPIRY_HOURS = 24

# ─── Number Filter ─────────────────────────────────────────────────────────────
# Leave empty to respond to everyone, or add numbers in E.164 format to whitelist.
ALLOWED_NUMBERS = set()

# ─── Typing Delay ──────────────────────────────────────────────────────────────
# Simulates a human typing the reply before sending.
# Delay is calculated from word count at TYPING_SPEED_WPM, then a random jitter
# of ±TYPING_JITTER_FRACTION is applied (e.g. 0.3 = ±30%).
TYPING_SPEED_WPM = 40          # words per minute (average human: 38-45)
TYPING_JITTER_FRACTION = 0.3   # randomness factor
TYPING_DELAY_MIN = 1.0         # minimum seconds before replying
TYPING_DELAY_MAX = 15.0        # cap so long messages don't stall too long
