# SMS AI Chatbot

An SMS chatbot powered by [Groq](https://console.groq.com) and [Vonage](https://vonage.com). When someone texts your Vonage number, the bot replies using a large language model — with per-sender conversation memory, a fully customizable persona, automatic contact learning, and a human-like typing delay.

Something not working? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

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
- **Optional webhook signature verification** — rejects spoofed requests when `VONAGE_SIGNATURE_SECRET` is set
- **Graceful error handling** — friendly fallback message if the AI API fails

---

## Project Structure

```
sms-chatbot/
├── app.py                # Flask server and Vonage webhook handler
├── config.py             # All settings: model, delays, filters, paths
├── conversation.py       # Per-sender conversation history with auto-expiry
├── profiles.py           # Persona loading and contact file management
├── send.py               # Standalone utility for sending one-off SMS messages
├── install.py            # One-time setup script — installs deps and configures .env
├── check_services.py     # Health check — verifies all services are running
├── persona.txt           # Who the bot is — edit this to change its identity
├── sms-chatbot.service   # Systemd service file for homelab/Linux deployment
├── contacts/             # Auto-created; one .txt file per phone number
├── logs/                 # Auto-created; daily rotating conversation logs
├── requirements.txt      # Python dependencies
├── .env.example          # Template for required environment variables
└── .gitignore
```

---

## Setup

### Automated setup (recommended)

After cloning, run the setup script — it installs dependencies, walks you through entering credentials, creates `persona.txt` if missing, and runs the health check at the end:

```bash
python3 -m venv venv
source venv/bin/activate
python install.py
```

Re-running it is safe; it only prompts for values that are missing from `.env`.

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

This is how Vonage tells your bot when a text message arrives.

1. Go to **Build & Manage** → **Numbers** → **Your Numbers**
2. Click the gear icon next to your number
3. Under **SMS**, set the **Inbound Webhook URL** to:
   ```
   https://yourdomain.com/sms
   ```
   (You'll get this URL in later steps — come back and fill it in once you have it)
4. Set the **HTTP Method** to `POST-Form`
5. Click **Save**

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
```

| Variable | Where to find it |
|---|---|
| `VONAGE_API_KEY` | Vonage dashboard → main page, top section |
| `VONAGE_API_SECRET` | Same location as API Key |
| `VONAGE_PHONE_NUMBER` | The number you bought in Step 4b (E.164 format, e.g. `+15551234567`) |
| `VONAGE_SIGNATURE_SECRET` | Account Settings → API Settings (optional) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys |

### Step 6 — Set up the bot's persona

Edit `persona.txt` to define who the bot is:

```
Your name is Alex. You are 26 years old and work as a personal assistant.
You are warm, witty, and direct. You have a dry sense of humor but are never mean.
Communicate casually over text — no corporate tone, no markdown formatting.
Keep replies short and natural since this is SMS, but be personal and genuine.
```

Be as specific as you want — the more detail, the more consistent the personality. The file is loaded once at startup, so restart the server after editing.

If `persona.txt` is missing, the bot falls back to the default `SYSTEM_PROMPT` in `config.py`.

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

1. Go to **Build & Manage** → **Numbers** → **Your Numbers** in the Vonage dashboard
2. Click the gear icon next to your number
3. Set the **Inbound Webhook URL** to your ngrok URL + `/sms`:
   ```
   https://abc123.ngrok-free.app/sms
   ```
4. Save

Text your Vonage number — the bot will reply.

> **Note:** Free ngrok URLs change every time you restart it. Update the webhook URL in the Vonage dashboard each session, or use a paid ngrok plan for a fixed URL.

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

Go to **Build & Manage** → **Numbers** → **Your Numbers** in the Vonage dashboard, click the gear icon, and set the **Inbound Webhook URL** to your stable public URL + `/sms`. Save.

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

Checks in order: env vars set, `persona.txt` present, Python packages installed, Groq API reachable, Vonage API reachable, Flask server on port 5000, and active ngrok tunnel. If an ngrok tunnel to port 5000 is found, it prints the full Vonage webhook URL so you can copy it directly.

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

---

## Security Notes

- **Never commit `.env`** — it's in `.gitignore` by default
- **`contacts/` and `logs/` are gitignored** — personal info and conversations stay local
- **Set `VONAGE_SIGNATURE_SECRET`** to enable HMAC webhook verification and reject spoofed requests
- **Use `ALLOWED_NUMBERS`** in `config.py` to restrict which numbers the bot responds to
