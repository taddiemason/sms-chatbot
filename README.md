# SMS + Telegram AI Chatbot

A multi-channel AI chatbot powered by [Groq](https://console.groq.com). It replies over **SMS** (via [Vonage](https://vonage.com)) and/or **Telegram** — with per-sender conversation memory, a fully customizable persona, automatic contact learning, and a human-like typing delay.

The two channels share the same brain (`brain.py`); only the thin send/receive edges differ. **Telegram needs no phone number and no public webhook** (it long-polls), which makes it a regulation-free way to let the bot message out when acquiring/registering an SMS number is a hurdle. Users opt in by pressing **Start** on the bot once.

Something not working? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Features

- **AI replies over SMS and Telegram** — powered by Groq's fast LLM inference (Llama 3.3 70B by default)
- **Telegram channel** — no phone number, no public webhook; runs as its own long-polling process alongside (or instead of) SMS
- **Shared brain** — persona, memory, contact learning, and typing delays are identical across both channels
- **Bot persona file** — define the bot's name, personality, and backstory in `persona.txt`
- **Per-contact memory** — the bot automatically learns and remembers facts about each person it talks to
- **Conversation history** — each sender gets their own rolling context window
- **Human-like typing delay** — replies sent after a realistic delay based on word count + random jitter
- **Conversation logs** — every message saved to daily rotating log files in `logs/`
- **Auto-expiry** — conversation history clears automatically after inactivity
- **Reset command** — users can text `reset` to wipe their history and start fresh
- **Number / chat ID whitelist** — optionally restrict SMS to specific phone numbers, or Telegram to specific chat IDs
- **Optional webhook signature verification** — rejects spoofed requests when `VONAGE_SIGNATURE_SECRET` is set
- **Graceful error handling** — friendly fallback message if the AI API fails

---

## Project Structure

```
sms-chatbot/
├── brain.py              # Channel-agnostic core: LLM call, memory, persona, typing delays
├── app.py                # SMS channel — Flask server and Vonage webhook handler
├── run_telegram.py       # Telegram channel — long-polling runner (no phone number/webhook)
├── channels/
│   ├── base.py           # Messenger interface (send(to, text))
│   ├── vonage_sms.py     # VonageMessenger — outbound SMS
│   └── telegram.py       # TelegramMessenger — send + long-polling
├── config.py             # All settings: model, delays, channel toggles, filters, paths
├── conversation.py       # Per-sender conversation history with auto-expiry
├── profiles.py           # Persona loading and contact file management
├── send.py               # Standalone utility for sending one-off SMS messages
├── install.py            # One-time setup script — installs deps and configures .env
├── check_services.py     # Health check — verifies all services are running
├── persona.txt           # Who the bot is — edit this to change its identity
├── sms-chatbot.service   # Systemd service file for homelab/Linux deployment
├── contacts/             # Auto-created; one .txt file per sender (phone number or chat ID)
├── logs/                 # Auto-created; daily rotating conversation logs
├── requirements.txt      # Python dependencies
├── .env.example          # Template for required environment variables
└── .gitignore
```

---

## Setup

### Automated setup (recommended)

After cloning, run the setup script:

```bash
python3 install.py
```

The installer walks you through every step with a progress counter (Step X of 8 for local, Step X of 9 for server):

- **Asks where you're setting up** — local machine (ngrok) or Linux server (gunicorn + systemd)
- **Installs dependencies** — creates and uses a virtualenv automatically for server setups
- **Guides credential entry** with validation on every field:
  - Vonage API key — checks 8-character alphanumeric format
  - Vonage API secret — checks minimum length
  - Vonage phone number — checks E.164 format (e.g. `+15551234567`)
  - Groq API key — checks `gsk_` prefix, then makes a live API call to confirm it works
  - Vonage key + secret validated together via a live API call — shows your account balance on success
  - Includes sign-up links if you don't have a Vonage or Groq account yet
  - If a field is wrong, shows the specific error and offers to retry before moving on
- **Interactive persona setup** — optionally set the bot's name, age, occupation, and personality right in the terminal
- **Vonage webhook guidance** — dedicated step with click-by-click instructions for pasting the webhook URL into the Vonage dashboard (the step most users get stuck on)
- **Health check** — verifies all services are reachable before finishing
- **Specific fix commands** printed for anything that fails

Re-running is safe — it skips values already set in `.env`. To redo all steps: `python install.py --reconfigure`

The manual steps below cover the same ground in detail if you prefer to set things up yourself or want to understand what the script does.

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/taddiemason/sms-chatbot.git
cd sms-chatbot
```

### Step 2 — Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2b — Create the logs directory

The bot writes conversation logs here — create it before starting the server:

```bash
mkdir -p logs
```

### Step 3 — Get a Groq API key

1. Go to [console.groq.com](https://console.groq.com) and sign in or create an account
2. Click **API Keys** in the left sidebar
3. Click **Create API Key**, give it a name, and copy the key (starts with `gsk_`)

The free tier is generous enough to run this bot without paying anything.

### Step 4 — Set up Vonage

#### 4a. Create an account and get credentials

1. Sign up at [vonage.com](https://vonage.com) (or log in)
2. From the dashboard, your **API Key** and **API Secret** are shown on the main page under your account name
3. Copy both — you'll need them for the `.env` file

#### 4b. Buy a phone number

1. In the Vonage dashboard, go to **Build & Manage** → **Numbers** → **Buy Numbers**
2. Search by country and select a number with SMS capability
3. Click **Buy** to confirm

#### 4c. Configure the inbound webhook

This is how Vonage tells your bot when a text message arrives. If you used `install.py`, it walks you through this step with click-by-click instructions once your public URL is known. For manual setup:

1. Go to **Build & Manage** → **Numbers** → **Your Numbers**
2. Click the gear icon (⚙) next to your number
3. Under **Messages**, set the **Inbound Webhook URL** to:
   ```
   https://yourdomain.com/sms
   ```
   (You'll get this URL in later steps — come back and fill it in once you have it)
4. Set the **HTTP Method** to `POST`
5. Click **Save changes**

#### 4d. (Optional) Enable webhook signature verification

If you want the bot to reject spoofed webhook requests:

1. In the Vonage dashboard, go to **Account Settings**
2. Under **API Settings**, find **Signature Secret** and generate or copy the secret
3. Add it to your `.env` as `VONAGE_SIGNATURE_SECRET`

Skip this for now if you just want to get running quickly — you can add it later.

### Step 5 — Configure your `.env` file

Copy the example file:

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```
VONAGE_API_KEY=xxxxxxxx
VONAGE_API_SECRET=xxxxxxxxxxxxxxxx
VONAGE_PHONE_NUMBER=+1xxxxxxxxxx
VONAGE_SIGNATURE_SECRET=            # leave blank to skip signature checks
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_BOT_TOKEN=                 # optional — only if running the Telegram channel
```

| Variable | Where to find it |
|---|---|
| `VONAGE_API_KEY` | Vonage dashboard → main page, top section (SMS channel) |
| `VONAGE_API_SECRET` | Same location as API Key (SMS channel) |
| `VONAGE_PHONE_NUMBER` | The number you bought in Step 4b (E.164 format, e.g. `+15551234567`) |
| `VONAGE_SIGNATURE_SECRET` | Account Settings → API Settings (optional) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys |
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) → `/newbot` (optional — Telegram channel only) |

> **SMS-only or Telegram-only?** The Vonage variables are only needed if you run the SMS channel (`app.py`), and `TELEGRAM_BOT_TOKEN` is only needed for the Telegram channel (`run_telegram.py`). `GROQ_API_KEY` is always required.

### Step 6 — Set up the bot's persona

If you used `install.py`, you were offered the option to customize the persona interactively (name, age, occupation, personality). If you chose the default or want to change it, edit `persona.txt` directly:

```
Your name is Alex. You are 26 years old and work as a personal assistant.
You are warm, witty, and direct. You have a dry sense of humor but are never mean.
Communicate casually over text — no corporate tone, no markdown formatting.
Keep replies short and natural since this is SMS, but be personal and genuine.
```

Be as specific as you want — the more detail, the more consistent the personality. The file is loaded once at startup, so restart the server after editing.

---

## Running Locally (Development)

Use this for testing before deploying to a server.

### Step 1 — Start the Flask server

```bash
python app.py
```

You should see:
```
2026-05-30 14:00:01 [PERSONA] Loaded: Your name is Alex...
 * Running on http://127.0.0.1:5000
```

### Step 2 — Expose it with ngrok

In a second terminal, run:

```bash
ngrok http 5000
```

Copy the `https://` forwarding URL from the output (e.g. `https://abc123.ngrok-free.app`).

### Step 3 — Set the Vonage webhook URL

If you used `install.py`, run `python check_services.py` to get your live ngrok URL, then follow the on-screen instructions from the installer's webhook step. For manual setup:

1. Go to **Build & Manage** → **Numbers** → **Your Numbers** in the Vonage dashboard
2. Click the gear icon (⚙) next to your number
3. Under **Messages**, set the **Inbound Webhook URL** to your ngrok URL + `/sms`:
   ```
   https://abc123.ngrok-free.app/sms
   ```
4. Set **HTTP Method** to `POST` and click **Save changes**

Text your Vonage number — the bot will reply.

> **Note:** Free ngrok URLs change every time you restart it. Update the webhook URL in the Vonage dashboard each session, or use a paid ngrok plan for a fixed URL.

---

## Running on Telegram

Telegram is a second channel that runs **independently** of SMS — it needs no phone number and no public webhook, because it long-polls Telegram's servers for incoming messages. You can run it alongside SMS, or on its own.

### Step 1 — Create a bot and get a token

1. In Telegram, open a chat with [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts (choose a name and a username ending in `bot`)
3. BotFather replies with a token like `123456789:ABCdef...` — copy it
4. Put it in your `.env` as `TELEGRAM_BOT_TOKEN` (the installer prompts for this too)

### Step 2 — Start the Telegram runner

```bash
python run_telegram.py
```

You should see `[TELEGRAM] Connected as @your_bot` followed by `[TELEGRAM] Long-polling started`.

### Step 3 — Talk to your bot

Open your bot in Telegram (`https://t.me/your_bot_username`), press **Start**, and send a message. The bot replies using the same persona, memory, and typing-delay behavior as SMS.

> **Why pressing Start matters:** Telegram bots can't message a user until that user has started the bot — that first message is how the bot learns the user's `chat_id` (it's logged on arrival). This is Telegram's built-in anti-spam consent, and it's why no phone number or A2P registration is involved. To restrict who the bot talks to, add chat IDs to `TELEGRAM_ALLOWED_CHAT_IDS` in `config.py`.

### Running both channels together

SMS and Telegram are separate processes — run them side by side:

```bash
# Terminal 1 (SMS):
python app.py            # or: gunicorn app:app

# Terminal 2 (Telegram):
python run_telegram.py
```

On a Linux server you can give Telegram its own systemd service (copy `sms-chatbot.service`, change `ExecStart` to `.../venv/bin/python run_telegram.py`, and name it e.g. `telegram-chatbot`). To disable Telegram without removing the token, set `ENABLE_TELEGRAM = False` in `config.py`.

---

## Deploying to a Homelab / Linux Server

For 24/7 operation, run the bot on a Linux server using gunicorn and a systemd service so it restarts automatically on crashes and reboots.

### Step 1 — Copy the project to your server

```bash
scp -r sms-chatbot/ youruser@yourserver:~/sms-chatbot
```

Or clone it directly on the server:

```bash
git clone https://github.com/taddiemason/sms-chatbot.git
cd sms-chatbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p logs
cp .env.example .env
# edit .env with your credentials
```

### Step 2 — Edit the service file

Open `sms-chatbot.service` and replace all instances of `/home/youruser/sms-chatbot` with your actual path. Make sure `ExecStart` points to the **venv's gunicorn**, not the system one — the system Python won't have the dependencies:

```ini
WorkingDirectory=/home/youruser/sms-chatbot
EnvironmentFile=/home/youruser/sms-chatbot/.env
ExecStart=/home/youruser/sms-chatbot/venv/bin/gunicorn app:app --workers 1 --threads 4 --bind 0.0.0.0:5000
Restart=always
RestartSec=5
StandardOutput=append:/home/youruser/sms-chatbot/logs/service.log
StandardError=append:/home/youruser/sms-chatbot/logs/service.log
```

> **Tip:** If the service starts but `logs/chat.log` stays empty, check for startup errors with:
> ```bash
> sudo journalctl -u sms-chatbot -n 50
> ```

### Step 3 — Install and enable the service

```bash
sudo cp sms-chatbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sms-chatbot   # start automatically on boot
sudo systemctl start sms-chatbot
sudo systemctl status sms-chatbot   # verify it's running
```

### Step 4 — Get a stable public HTTPS URL

The bot needs a public HTTPS URL so Vonage can reach it. Two options:

**Option A — Cloudflare Tunnel (recommended)**

Free, gives a stable URL on your own domain, no port forwarding or SSL certs required. Requires a domain pointed at Cloudflare.

```bash
# Install cloudflared on the server
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/

# Authenticate and create the tunnel
cloudflared tunnel login
cloudflared tunnel create sms-chatbot
```

Copy the tunnel UUID from the output — you'll need it in the config file.

```bash
# Create the config directory and file
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Paste the following into the file, replacing the tunnel UUID and your domain:

```yaml
tunnel: YOUR-TUNNEL-UUID
credentials-file: /home/youruser/.cloudflared/YOUR-TUNNEL-UUID.json

ingress:
  - hostname: yourdomain.com
    service: http://localhost:5000
  - service: http_status:404
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter`), then route your domain and install the service:

```bash
cloudflared tunnel route dns sms-chatbot yourdomain.com

# Install as a systemd service so it runs on boot
sudo cloudflared service install
```

Your webhook URL will be: `https://yourdomain.com/sms`

**Option B — ngrok on the server**

Simpler if you don't have a domain. Install ngrok on the server and run it there. The free tier changes the URL on restart; a paid plan gives a fixed URL.

### Step 5 — Update the Vonage webhook URL

If you used `install.py`, it prompted for your domain and printed the exact URL and click-by-click instructions. For manual setup:

1. Go to **Build & Manage** → **Numbers** → **Your Numbers** in the Vonage dashboard
2. Click the gear icon (⚙) next to your number
3. Under **Messages**, set **Inbound Webhook URL** to your public domain + `/sms`:
   ```
   https://yourdomain.com/sms
   ```
4. Set **HTTP Method** to `POST` and click **Save changes**

---

## Persona & Contact Files

### Bot persona — `persona.txt`

Defines who the bot is. Loaded once at startup — restart the server after editing.

### Contact files — `contacts/<number>.txt`

After every exchange, the bot automatically extracts facts from the conversation and saves them:

```
- Name: Jordan
- Works in marketing
- Has a dog named Max (golden retriever)
- Going on vacation to Mexico in June
```

You can also edit these files manually — changes take effect on the next incoming message without restarting. The `contacts/` folder is gitignored so personal info never gets committed.

Set `AUTO_UPDATE_CONTACTS = False` in `config.py` to disable automatic learning.

---

## Configuration

All settings live in `config.py`. Restart the server after making changes.

### Channels

| Setting | Default | Description |
|---|---|---|
| `ENABLE_TELEGRAM` | `True` | Whether `run_telegram.py` starts the Telegram poller |

SMS is served by `app.py` (Vonage webhook); Telegram is served by `run_telegram.py` (long-polling). Each runs as its own process.

### AI

| Setting | Default | Description |
|---|---|---|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model used for replies |
| `MAX_TOKENS` | `300` | Max reply length (~225 words) |

Available Groq models:

| Model | Speed | Notes |
|---|---|---|
| `llama-3.3-70b-versatile` | Fast | Default — best quality/speed balance |
| `llama-3.1-8b-instant` | Very fast | Good for simple conversations |
| `mixtral-8x7b-32768` | Fast | Larger context window |

### Conversation Memory

| Setting | Default | Description |
|---|---|---|
| `MAX_HISTORY_MESSAGES` | `20` | Messages to keep per sender (user + bot combined) |
| `CONVERSATION_EXPIRY_HOURS` | `24` | Hours of inactivity before history auto-clears |

### Contact Learning

| Setting | Default | Description |
|---|---|---|
| `AUTO_UPDATE_CONTACTS` | `True` | Auto-extract facts into contact files after each exchange |
| `CONTACTS_DIR` | `"contacts"` | Folder where contact files are stored |

### Sender Filters

SMS filters on phone number; Telegram filters on chat ID. Both default to empty (respond to everyone):

```python
ALLOWED_NUMBERS = set()            # SMS — empty = respond to everyone
TELEGRAM_ALLOWED_CHAT_IDS = set()  # Telegram — empty = respond to everyone
```

To restrict to specific senders:

```python
ALLOWED_NUMBERS = {"+15551234567", "+15559876543"}
TELEGRAM_ALLOWED_CHAT_IDS = {"123456789"}   # chat IDs are logged on first message
```

### Typing Delay

| Setting | Default | Description |
|---|---|---|
| `TYPING_SPEED_WPM` | `40` | Words per minute (human avg: 38–45) |
| `TYPING_JITTER_FRACTION` | `0.3` | ±30% random variation |
| `TYPING_DELAY_MIN` | `1.0` | Minimum seconds before sending |
| `TYPING_DELAY_MAX` | `15.0` | Maximum seconds before sending |

---

## Usage Commands

### Conversation

| Action | How |
|---|---|
| Start chatting | Text your Vonage number — the bot replies automatically |
| Reset history | Text `reset` (case-insensitive) to wipe your conversation and start fresh |

### Health check

Verify that all required services are reachable before starting (or to diagnose issues):

```bash
python check_services.py
```

Checks in order: env vars set, `persona.txt` present, Python packages installed, Groq API reachable, Vonage API reachable, Telegram API reachable (if `TELEGRAM_BOT_TOKEN` is set), Flask server on port 5000, and active ngrok tunnel. If an ngrok tunnel to port 5000 is found, it prints the full Vonage webhook URL so you can copy it directly.

Exits with code `0` if everything passes, `1` if anything needs attention. Can be chained:

```bash
python check_services.py && python app.py
```

---

### Viewing logs

Follow the conversation log in real time:

```bash
tail -f logs/chat.log
```

View the last 50 log lines:

```bash
tail -n 50 logs/chat.log
```

Search for a specific number's messages:

```bash
grep "+15551234567" logs/chat.log
```

View service-level logs (gunicorn startup, crashes, errors):

```bash
tail -f logs/service.log
```

Stream systemd journal output (alternative to the log file):

```bash
journalctl -u sms-chatbot -f
```

### Managing the service (Linux/systemd)

```bash
sudo systemctl status sms-chatbot    # check if it's running
sudo systemctl start sms-chatbot     # start the bot
sudo systemctl stop sms-chatbot      # stop the bot
sudo systemctl restart sms-chatbot   # restart (e.g. after editing config.py or persona.txt)
sudo systemctl disable sms-chatbot   # stop it from starting on boot
```

### Reloading the persona

The persona is loaded at startup, so after editing `persona.txt`:

```bash
sudo systemctl restart sms-chatbot
```

Or if running locally:

```bash
# Stop the running server (Ctrl+C), then:
python app.py
```

### Manually sending an SMS

Use `send.py` to fire off a one-off text from the command line:

```bash
python send.py "+15551234567" "Hello from the bot"
```

### Editing a contact file

Open any contact file directly to add, correct, or remove facts:

```bash
nano contacts/+15551234567.txt
```

Changes take effect on the next incoming message — no restart needed.

---

## How It Works

```
User texts Vonage number
        │
        ▼
Vonage sends HTTP POST to /sms webhook (form-encoded body)
        │
        ▼
(Optional) Server verifies HMAC signature — rejects spoofed requests
        │
        ├─ "reset"? → clear history, send confirmation
        ├─ Number not in whitelist? → ignore
        ├─ Empty message? → ignore
        │
        ▼
Load persona.txt + contacts/<number>.txt → build system prompt
        │
        ▼
Groq API called with system prompt + conversation history
        │
        ▼
200 returned to Vonage immediately (avoids webhook timeout)
        │
        ▼
Background thread: sleep(typing delay) → send SMS via Vonage REST API
        │
        ▼
Background thread: extract new facts → append to contacts/<number>.txt
        │
        ▼
Everything logged to logs/chat.log
```

**Telegram follows the same path**, only the edges differ: `run_telegram.py` long-polls `getUpdates`, applies the `TELEGRAM_ALLOWED_CHAT_IDS` filter, and calls the same `brain.process_message(messenger, chat_id, text)`. Replies are sent via the Telegram Bot API instead of Vonage. Memory and contact files are keyed by `chat_id` rather than phone number.

---

## Security Notes

- **Never commit `.env`** — it's in `.gitignore` by default
- **`contacts/` and `logs/` are gitignored** — personal info and conversations stay local
- **Set `VONAGE_SIGNATURE_SECRET`** to enable HMAC webhook verification and reject spoofed requests
- **Use `ALLOWED_NUMBERS` / `TELEGRAM_ALLOWED_CHAT_IDS`** in `config.py` to restrict which SMS numbers or Telegram chat IDs the bot responds to
- **`TELEGRAM_BOT_TOKEN` is a secret** — anyone with it controls your bot; keep it in `.env` only
