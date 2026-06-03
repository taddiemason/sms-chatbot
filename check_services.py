#!/usr/bin/env python3
"""Run this to verify every service the SMS chatbot depends on is reachable."""

import os
import sys
import socket

# Enable ANSI color codes on Windows
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

def _load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
OK     = f"{GREEN}✓{RESET}"
FAIL   = f"{RED}✗{RESET}"
WARN   = f"{YELLOW}!{RESET}"

passed = 0
failed = 0


def check(label, ok, detail=""):
    global passed, failed
    icon = OK if ok else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  {icon}  {label}{suffix}")
    if ok:
        passed += 1
    else:
        failed += 1
    return ok


def warn(label, detail=""):
    suffix = f"  ({detail})" if detail else ""
    print(f"  {WARN}  {label}{suffix}")


# ── 1. Environment variables ──────────────────────────────────────────────────
print(f"\n{YELLOW}Environment variables{RESET}")

required = ["VONAGE_API_KEY", "VONAGE_API_SECRET", "VONAGE_PHONE_NUMBER", "GROQ_API_KEY"]
for var in required:
    val = os.environ.get(var, "")
    check(var, bool(val), "set" if val else f"{RED}MISSING{RESET} — add to .env")

sig = os.environ.get("VONAGE_SIGNATURE_SECRET", "")
warn("VONAGE_SIGNATURE_SECRET", "set" if sig else "not set — webhook signature verification disabled")

tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
warn("TELEGRAM_BOT_TOKEN", "set" if tg_token else "not set — Telegram channel disabled (run_telegram.py)")

# ── 2. Required files ─────────────────────────────────────────────────────────
print(f"\n{YELLOW}Required files{RESET}")

try:
    from config import PERSONA_FILE, CONTACTS_DIR, LOGS_DIR
except Exception as e:
    check("config.py", False, str(e))
    PERSONA_FILE, CONTACTS_DIR, LOGS_DIR = "persona.txt", "contacts", "logs"

check("persona.txt", os.path.isfile(PERSONA_FILE), PERSONA_FILE)
warn("contacts/", "exists" if os.path.isdir(CONTACTS_DIR) else "will be auto-created on first run")
warn("logs/",     "exists" if os.path.isdir(LOGS_DIR)     else "will be auto-created on first run")

# ── 3. Python packages ────────────────────────────────────────────────────────
print(f"\n{YELLOW}Python packages{RESET}")

pkg_map = {
    "flask":      "flask",
    "vonage":     "vonage",
    "vonage_sms": "vonage_sms",
    "groq":       "groq",
    "dotenv":     "dotenv",
    "gunicorn":   "gunicorn",
    "requests":   "requests",
}
for display, import_name in pkg_map.items():
    try:
        __import__(import_name)
        check(display, True)
    except ImportError:
        check(display, False, "not installed — run: pip install -r requirements.txt")

# ── 4. Groq API ───────────────────────────────────────────────────────────────
print(f"\n{YELLOW}Groq API{RESET}")

api_key = os.environ.get("GROQ_API_KEY", "")
if not api_key:
    check("Groq API key", False, "GROQ_API_KEY not set")
else:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        models = client.models.list()
        check("Groq API", True, f"{len(models.data)} models available")
    except Exception as e:
        msg = str(e)
        if "401" in msg or "auth" in msg.lower() or "invalid" in msg.lower():
            check("Groq API", False, "authentication failed — check GROQ_API_KEY")
        else:
            check("Groq API", False, msg[:80])

# ── 5. Vonage API ─────────────────────────────────────────────────────────────
print(f"\n{YELLOW}Vonage API{RESET}")

vonage_key    = os.environ.get("VONAGE_API_KEY", "")
vonage_secret = os.environ.get("VONAGE_API_SECRET", "")
vonage_number = os.environ.get("VONAGE_PHONE_NUMBER", "")

if not vonage_key or not vonage_secret:
    check("Vonage credentials", False, "VONAGE_API_KEY or VONAGE_API_SECRET not set")
else:
    try:
        from vonage import Auth, Vonage
        client = Vonage(Auth(api_key=vonage_key, api_secret=vonage_secret))
        balance = client.account.get_balance()
        check("Vonage API", True, f"balance: {balance.value:.4f}")
    except Exception as e:
        msg = str(e)
        if "401" in msg or "auth" in msg.lower() or "invalid" in msg.lower():
            check("Vonage API", False, "authentication failed — check VONAGE_API_KEY / VONAGE_API_SECRET")
        else:
            check("Vonage API", False, msg[:80])

if vonage_number:
    check("VONAGE_PHONE_NUMBER", True, vonage_number)
else:
    check("VONAGE_PHONE_NUMBER", False, "not set")

# ── 5b. Telegram API (optional) ───────────────────────────────────────────────
print(f"\n{YELLOW}Telegram API{RESET}")

if not tg_token:
    warn("Telegram", "TELEGRAM_BOT_TOKEN not set — skipping (channel disabled)")
else:
    try:
        import requests
        resp = requests.get(f"https://api.telegram.org/bot{tg_token}/getMe", timeout=10).json()
        if resp.get("ok"):
            check("Telegram API", True, f"@{resp['result'].get('username')}")
        else:
            check("Telegram API", False, resp.get("description", "getMe failed — check TELEGRAM_BOT_TOKEN"))
    except Exception as e:
        check("Telegram API", False, str(e)[:80])

# ── 6. Flask server ───────────────────────────────────────────────────────────
print(f"\n{YELLOW}Flask server (localhost:5000){RESET}")

try:
    with socket.create_connection(("127.0.0.1", 5000), timeout=2):
        check("Port 5000", True, "server is running")
except (socket.timeout, ConnectionRefusedError, OSError):
    check("Port 5000", False, "not running — start with: python app.py")

# ── 7. Systemd services (Linux only) ─────────────────────────────────────────
if sys.platform != "win32" and os.path.isdir("/etc/systemd"):
    import subprocess as _sp
    print(f"\n{YELLOW}Systemd services{RESET}")
    for svc in ("sms-chatbot", "ngrok"):
        r = _sp.run(["systemctl", "is-active", svc], capture_output=True, text=True)
        active = r.stdout.strip() == "active"
        check(f"{svc}", active,
              "active" if active else f"not running — sudo systemctl start {svc}")

# ── 8. Ngrok tunnel ───────────────────────────────────────────────────────────
print(f"\n{YELLOW}Ngrok tunnel{RESET}")

import json
import urllib.request
import urllib.error

try:
    with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as resp:
        data = json.loads(resp.read())
    tunnels = data.get("tunnels", [])

    # Find tunnels that forward to port 5000
    bot_tunnels = [
        t for t in tunnels
        if "5000" in t.get("config", {}).get("addr", "")
    ]

    if bot_tunnels:
        for t in bot_tunnels:
            public_url = t.get("public_url", "")
            proto = t.get("proto", "")
            if proto == "https":
                webhook_url = public_url.rstrip("/") + "/sms"
                check("Ngrok tunnel (https)", True, public_url)
                print(f"       {YELLOW}→ Vonage webhook URL:{RESET} {webhook_url}")
            else:
                check(f"Ngrok tunnel ({proto})", True, public_url)
    else:
        # Ngrok is running but not tunneling port 5000
        all_urls = [t.get("public_url", "") for t in tunnels]
        check("Ngrok tunnel to :5000", False,
              f"ngrok running but no tunnel to port 5000 (active: {', '.join(all_urls) or 'none'})")

except urllib.error.URLError:
    check("Ngrok", False, "not running — start with: ngrok http 5000")

# ── Summary ───────────────────────────────────────────────────────────────────
total = passed + failed
print(f"\n{'─' * 48}")
if failed == 0:
    print(f"  {GREEN}{passed}/{total} checks passed — everything looks good!{RESET}\n")
else:
    print(f"  {passed}/{total} checks passed  {RED}{failed} issue(s) need attention{RESET}\n")

sys.exit(0 if failed == 0 else 1)
