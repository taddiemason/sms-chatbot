# SMS AI Chatbot

An SMS chatbot powered by [Groq](https://console.groq.com) and [Twilio](https://www.twilio.com). When someone texts your Twilio number, the bot replies using a large language model — with per-sender conversation memory, a fully customizable personality, and a human-like typing delay before sending.

---

## Features

- **AI replies over SMS** — powered by Groq's fast LLM inference (Llama 3.3 70B by default)
- **Conversation memory** — each sender gets their own context window; the bot remembers past messages
- **Custom system prompt** — define the bot's name, personality, tone, and rules in one place
- **Human-like typing delay** — replies are sent after a realistic delay based on word count
- **Auto-expiry** — conversation history clears automatically after a period of inactivity
- **Reset command** — users can text `reset` to wipe their history and start fresh
- **Number whitelist** — optionally restrict the bot to respond only to specific phone numbers
- **Twilio request validation** — rejects spoofed webhook requests not signed by Twilio
- **Graceful error handling** — if the AI API fails, the user gets a friendly message instead of silence

---

## Requirements

- Python 3.10+
- A [Twilio account](https://www.twilio.com) with a phone number
- A [Groq API key](https://console.groq.com) (free tier available)
- [ngrok](https://ngrok.com) for local development, or a hosted server for production

---

## Project Structure

```
sms-chatbot/
├── app.py            # Flask server and Twilio webhook handler
├── config.py         # All settings: system prompt, model, delays, filters
├── conversation.py   # Per-sender conversation history with auto-expiry
├── requirements.txt  # Python dependencies
├── .env.example      # Template for required environment variables
└── .gitignore
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/taddiemason/sms-chatbot.git
cd sms-chatbot
pip install -r requirements.txt
```

### 2. Create your `.env` file

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` and set the following:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

| Variable | Where to find it |
|---|---|
| `TWILIO_ACCOUNT_SID` | [Twilio Console](https://console.twilio.com) → Account Info |
| `TWILIO_AUTH_TOKEN` | Same page, below the SID |
| `TWILIO_PHONE_NUMBER` | Twilio Console → Phone Numbers → your number (in E.164 format, e.g. `+15551234567`) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys |

### 3. Customize the bot

Open `config.py` to configure the bot's behavior:

```python
SYSTEM_PROMPT = """You are a friendly assistant communicating over SMS.
Keep replies concise. Never use markdown formatting."""
```

This is where you define the bot's personality. See the [Configuration](#configuration) section for all available settings.

### 4. Run the server

```bash
python app.py
```

The server starts on port `5000`.

### 5. Expose it with ngrok

In a second terminal:

```bash
ngrok http 5000
```

Copy the `https://` URL ngrok gives you (e.g. `https://abc123.ngrok.io`).

### 6. Wire up Twilio

1. Go to [Twilio Console](https://console.twilio.com) → **Phone Numbers** → your number
2. Under **Messaging**, find **"A message comes in"**
3. Set the webhook URL to your ngrok URL + `/sms`:
   ```
   https://abc123.ngrok.io/sms
   ```
4. Make sure the method is set to **HTTP POST**
5. Save

Text your Twilio number — the bot will reply.

---

## Configuration

All settings live in `config.py`. Restart the server after making changes.

### AI Behavior

```python
SYSTEM_PROMPT = "..."
```
Controls the bot's entire personality, tone, rules, and knowledge. Be specific — the more detail you provide, the more consistent the bot's behavior.

**Examples:**
```python
# Customer support agent
SYSTEM_PROMPT = """You are Alex, a support agent for Acme Corp.
Only answer questions about our products. If you can't help, say so politely.
Never discuss competitors. Keep replies under 3 sentences."""

# Personal assistant
SYSTEM_PROMPT = """You are a personal assistant. Be direct and concise.
The user's name is Jordan. Remember their preferences as they share them."""
```

```python
GROQ_MODEL = "llama-3.3-70b-versatile"
```
The Groq model to use. Options:
| Model | Speed | Notes |
|---|---|---|
| `llama-3.3-70b-versatile` | Fast | Default — best balance of quality and speed |
| `llama-3.1-8b-instant` | Very fast | Smaller, good for simple conversations |
| `mixtral-8x7b-32768` | Fast | Larger context window |

```python
MAX_TOKENS = 300
```
Maximum length of the AI's reply. 300 tokens ≈ ~225 words, which is comfortable for SMS.

### Conversation Memory

```python
MAX_HISTORY_MESSAGES = 20
```
How many messages (user + assistant combined) to remember per sender. Higher values give the bot more context but use more tokens per request.

```python
CONVERSATION_EXPIRY_HOURS = 24
```
If a sender hasn't texted in this many hours, their history is automatically cleared on their next message. Set to a large number (e.g. `999`) to effectively disable expiry.

### Number Filter

```python
ALLOWED_NUMBERS = set()
```
Leave empty to respond to everyone. Add numbers in E.164 format to whitelist specific senders:

```python
ALLOWED_NUMBERS = {"+15551234567", "+15559876543"}
```

Texts from numbers not in the list are silently ignored.

### Typing Delay

Simulates a human typing before sending the reply.

```python
TYPING_SPEED_WPM = 40        # words per minute (human average: 38–45)
TYPING_JITTER_FRACTION = 0.3 # ±30% random variation per message
TYPING_DELAY_MIN = 1.0       # always wait at least this many seconds
TYPING_DELAY_MAX = 15.0      # never wait longer than this
```

The delay is calculated from the word count of the reply, then random jitter is applied to make it feel natural. Set `TYPING_DELAY_MIN = 0` and `TYPING_DELAY_MAX = 0` to disable.

---

## Usage

### Normal conversation

Just text the Twilio number. The bot replies based on your system prompt and remembers the conversation.

### Reset history

Text `reset` (case-insensitive) to wipe your conversation history and start fresh. The bot replies with a confirmation message.

---

## How It Works

```
User texts Twilio number
        │
        ▼
Twilio sends HTTP POST to /sms (your server)
        │
        ▼
Server validates Twilio signature (rejects spoofed requests)
        │
        ├─ "reset" command? → clear history, send confirmation, done
        │
        ▼
User message added to conversation history
        │
        ▼
Groq API called with system prompt + full conversation history
        │
        ▼
AI reply added to conversation history
        │
        ▼
Empty response sent back to Twilio immediately (avoids timeout)
        │
        ▼
Background thread waits (typing delay) then sends SMS via Twilio REST API
        │
        ▼
User receives reply
```

---

## Deploying to Production

For a permanent public URL (instead of ngrok), deploy the Flask app to any hosting platform:

| Platform | Notes |
|---|---|
| [Railway](https://railway.app) | Free tier, easy deploy from GitHub |
| [Render](https://render.com) | Free tier with auto-deploy from GitHub |
| [Fly.io](https://fly.io) | More control, generous free tier |

After deploying, update your Twilio webhook URL from the ngrok URL to your production URL.

Make sure to set your environment variables (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `GROQ_API_KEY`) in the platform's dashboard — never commit your `.env` file.

---

## Security Notes

- **Never commit `.env`** — it's listed in `.gitignore` by default
- **Twilio request validation** is enabled by default — every webhook is verified to be signed by Twilio
- **Number whitelisting** via `ALLOWED_NUMBERS` adds an extra layer if you want a private bot
