# SMS AI Chatbot

An SMS chatbot powered by [Groq](https://console.groq.com) and [Twilio](https://www.twilio.com). When someone texts your Twilio number, the bot replies using a large language model — with per-sender conversation memory, a fully customizable persona, automatic contact learning, and a human-like typing delay.

---

## Features

- **AI replies over SMS** — powered by Groq's fast LLM inference (Llama 3.3 70B by default)
- **Bot persona file** — define the bot's name, personality, and backstory in `persona.txt`
- **Per-contact memory** — the bot automatically learns and remembers facts about each person it talks to
- **Conversation history** — each sender gets their own rolling context window
- **Human-like typing delay** — replies sent after a realistic delay based on word count + random jitter
- **Conversation logs** — every message saved to daily rotating log files in `logs/`
- **Auto-expiry** — conversation history clears automatically after inactivity
- **Reset command** — users can text `reset` to wipe their history and start fresh
- **Number whitelist** — optionally restrict the bot to specific phone numbers only
- **Twilio request validation** — rejects spoofed webhook requests not signed by Twilio
- **Graceful error handling** — friendly fallback message if the AI API fails

---

## Requirements

- Python 3.10+
- A [Twilio account](https://www.twilio.com) with a phone number (~$1/month)
- A [Groq API key](https://console.groq.com) (free tier available)
- [ngrok](https://ngrok.com) for local development, or a hosted server for production

---

## Project Structure

```
sms-chatbot/
├── app.py              # Flask server and Twilio webhook handler
├── config.py           # All settings: model, delays, filters, paths
├── conversation.py     # Per-sender conversation history with auto-expiry
├── profiles.py         # Persona loading and contact file management
├── persona.txt         # Who the bot is — edit this to change its identity
├── contacts/           # Auto-created; one .txt file per phone number
├── logs/               # Auto-created; daily rotating conversation logs
├── requirements.txt    # Python dependencies
├── .env.example        # Template for required environment variables
└── .gitignore
```

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/taddiemason/sms-chatbot.git
cd sms-chatbot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your `.env` file

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` and set:

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
| `TWILIO_PHONE_NUMBER` | Twilio Console → Phone Numbers → your number (E.164 format, e.g. `+15551234567`) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys |

### 4. Set up the bot's persona

Edit `persona.txt` to define who the bot is:

```
Your name is Alex. You are 26 years old and work as a personal assistant.
You are warm, witty, and direct. You have a dry sense of humor but are never mean.
Communicate casually over text — no corporate tone, no markdown formatting.
Keep replies short and natural since this is SMS, but be personal and genuine.
```

Be as detailed as you want — the more specific, the more consistent the bot's personality.

---

## Launching the Bot

### Step 1 — Start the server

```bash
python app.py
```

You should see:
```
2026-05-30 14:00:01 [PERSONA] Loaded: Your name is Alex...
```

The server runs on port `5000`.

### Step 2 — Expose it with ngrok

Open a second terminal and run:

```bash
ngrok http 5000
```

Copy the `https://` forwarding URL (e.g. `https://abc123.ngrok.io`).

### Step 3 — Wire up Twilio

1. Go to [Twilio Console](https://console.twilio.com) → **Phone Numbers** → your number
2. Under **Messaging → "A message comes in"**, set the webhook to your ngrok URL + `/sms`:
   ```
   https://abc123.ngrok.io/sms
   ```
3. Set the method to **HTTP POST** and save

Text your Twilio number — the bot will reply.

> **Note:** ngrok URLs change every time you restart it. Update the Twilio webhook URL each session, or use a paid ngrok plan for a fixed URL.

---

## Persona & Contact Files

### Bot persona — `persona.txt`

This file defines who the bot is. Edit it freely — it's loaded once when the server starts, so restart after making changes.

If `persona.txt` is missing, the bot falls back to `SYSTEM_PROMPT` in `config.py`.

### Contact files — `contacts/<number>.txt`

The bot automatically creates and updates a file for each person it talks to. After every exchange, a fast AI call extracts any new facts and appends them:

```
- Name: Jordan
- Works in marketing
- Has a dog named Max (golden retriever)
- Going on vacation to Mexico in June
```

You can also edit these files manually — changes take effect on the next incoming message without restarting the server. The `contacts/` folder is gitignored so personal info never gets committed.

Set `AUTO_UPDATE_CONTACTS = False` in `config.py` to disable automatic learning.

---

## Conversation Logs

All messages are logged to `logs/chat.log` while the server is running:

```
2026-05-30 14:02:11 [IN]   +15551234567: hey whats up
2026-05-30 14:02:14 [OUT]  +15551234567 in 3.2s: Not much, just hanging. What's going on?
2026-05-30 14:02:17 [SENT] +15551234567: Not much, just hanging. What's going on?
2026-05-30 14:02:18 [PROFILE] Updated contact for +15551234567: - Name: Jordan
```

Logs rotate daily. Old files are saved as `logs/chat.log.2026-05-29` and kept for 30 days. The `logs/` folder is gitignored.

---

## Usage

### Normal conversation

Text the Twilio number. The bot replies based on the persona and remembers the conversation.

### Reset history

Text `reset` (case-insensitive) to wipe your conversation history and start fresh.

---

## Configuration

All settings live in `config.py`. Restart the server after making changes.

### AI

| Setting | Default | Description |
|---|---|---|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model used for replies |
| `MAX_TOKENS` | `300` | Max reply length (~225 words) |

Available models:
| Model | Speed | Notes |
|---|---|---|
| `llama-3.3-70b-versatile` | Fast | Default — best quality/speed balance |
| `llama-3.1-8b-instant` | Very fast | Good for simple conversations |
| `mixtral-8x7b-32768` | Fast | Larger context window |

### Memory

| Setting | Default | Description |
|---|---|---|
| `MAX_HISTORY_MESSAGES` | `20` | Messages to keep per sender (user + bot combined) |
| `CONVERSATION_EXPIRY_HOURS` | `24` | Hours of inactivity before history auto-clears |

### Contact Learning

| Setting | Default | Description |
|---|---|---|
| `AUTO_UPDATE_CONTACTS` | `True` | Whether to auto-extract facts into contact files |
| `CONTACTS_DIR` | `"contacts"` | Folder where contact files are stored |

### Number Filter

```python
ALLOWED_NUMBERS = set()  # empty = respond to everyone
```

To restrict to specific numbers:
```python
ALLOWED_NUMBERS = {"+15551234567", "+15559876543"}
```

### Typing Delay

| Setting | Default | Description |
|---|---|---|
| `TYPING_SPEED_WPM` | `40` | Words per minute (human avg: 38–45) |
| `TYPING_JITTER_FRACTION` | `0.3` | ±30% random variation |
| `TYPING_DELAY_MIN` | `1.0` | Minimum delay in seconds |
| `TYPING_DELAY_MAX` | `15.0` | Maximum delay in seconds |

---

## How It Works

```
User texts Twilio number
        │
        ▼
Twilio sends HTTP POST to /sms webhook
        │
        ▼
Server validates Twilio signature (rejects spoofed requests)
        │
        ├─ "reset"? → clear history, send confirmation
        │
        ▼
Load persona.txt + contacts/<number>.txt → build system prompt
        │
        ▼
Groq API called with system prompt + conversation history
        │
        ▼
Empty response returned to Twilio immediately (avoids 15s timeout)
        │
        ▼
Background thread: sleep(typing delay) → send SMS via Twilio REST API
        │
        ▼
Background thread: extract new facts → append to contacts/<number>.txt
        │
        ▼
Everything logged to logs/chat.log
```

---

## Deploying to Production

For a permanent public URL instead of ngrok:

| Platform | Notes |
|---|---|
| [Railway](https://railway.app) | Free tier, one-click deploy from GitHub |
| [Render](https://render.com) | Free tier, auto-deploys on git push |
| [Fly.io](https://fly.io) | More control, generous free tier |

After deploying, set your environment variables in the platform's dashboard and update the Twilio webhook URL to your production URL.

---

## Security Notes

- **Never commit `.env`** — it's in `.gitignore` by default
- **`contacts/` and `logs/` are gitignored** — personal info and conversations stay local
- **Twilio request validation** is enabled — every webhook verified to be signed by Twilio
- **Number whitelisting** via `ALLOWED_NUMBERS` restricts who can interact with the bot
