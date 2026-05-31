#!/usr/bin/env python3
"""One-time setup script — installs dependencies and walks through configuration."""

import os
import sys
import subprocess
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))

# ── ANSI colors ───────────────────────────────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )
    except Exception:
        pass

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def section(title):
    print(f"\n{BOLD}{CYAN}── {title} {'─' * (44 - len(title))}{RESET}")

def ok(msg):   print(f"  {GREEN}✓{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}")
def info(msg): print(f"  {YELLOW}→{RESET}  {msg}")

def prompt(label, default="", secret=False):
    hint = f" {DIM}[{default}]{RESET}" if default else ""
    marker = f" {DIM}(optional — press Enter to skip){RESET}" if not default and secret else ""
    try:
        value = input(f"  {CYAN}?{RESET}  {label}{hint}{marker}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(0)
    return value or default

errors = []

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}SMS Chatbot — Setup{RESET}")
print(f"{DIM}Installs dependencies and walks through all required configuration.{RESET}")

# ── Step 1: Python version ────────────────────────────────────────────────────
section("1  Python version")
major, minor = sys.version_info[:2]
if (major, minor) < (3, 8):
    fail(f"Python 3.8+ required, found {major}.{minor}")
    sys.exit(1)
ok(f"Python {major}.{minor}")

# ── Step 2: pip packages ──────────────────────────────────────────────────────
section("2  Python packages")
req = os.path.join(HERE, "requirements.txt")
if not os.path.isfile(req):
    fail("requirements.txt not found — are you in the right directory?")
    sys.exit(1)

info("Running pip install -r requirements.txt ...")
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", req, "--quiet"],
    capture_output=True, text=True,
)
if result.returncode != 0:
    fail("pip install failed:\n" + result.stderr)
    sys.exit(1)
ok("All packages installed")

# ── Step 3: .env file ─────────────────────────────────────────────────────────
section("3  Environment variables  (.env)")

env_path = os.path.join(HERE, ".env")

# Load whatever is already in .env
existing = {}
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    info("Existing .env found — only prompting for missing or empty values\n")
else:
    info("No .env found — let's create one\n")

values = dict(existing)

def collect(key, label, required=True):
    current = values.get(key, "")
    if current:
        ok(f"{key}  {DIM}(already set){RESET}")
        return
    while True:
        val = prompt(label, secret=not required)
        if val:
            values[key] = val
            return
        if not required:
            return
        print(f"  {RED}  Required — please enter a value.{RESET}")

print(f"  {DIM}Vonage — sign in at dashboard.nexmo.com{RESET}")
collect("VONAGE_API_KEY",       "Vonage API key")
collect("VONAGE_API_SECRET",    "Vonage API secret")
collect("VONAGE_PHONE_NUMBER",  "Vonage phone number  (E.164 format, e.g. +15551234567)")
print()
print(f"  {DIM}Groq — get a key at console.groq.com{RESET}")
collect("GROQ_API_KEY",         "Groq API key  (starts with gsk_)")
print()
print(f"  {DIM}Optional — enables HMAC signature verification on incoming webhooks{RESET}")
collect("VONAGE_SIGNATURE_SECRET", "Vonage signature secret", required=False)

with open(env_path, "w", encoding="utf-8") as f:
    for k, v in values.items():
        f.write(f"{k}={v}\n")
ok(".env saved")

# ── Step 4: persona.txt ───────────────────────────────────────────────────────
section("4  Bot persona  (persona.txt)")

persona_path = os.path.join(HERE, "persona.txt")
if os.path.isfile(persona_path):
    ok("persona.txt already exists")
else:
    info("No persona.txt found — creating a default one")
    default = (
        "You are a friendly and helpful assistant communicating over SMS.\n"
        "Keep replies concise and clear — SMS has limited space.\n"
        "Never use markdown formatting like ** or # since it won't render in SMS.\n"
    )
    with open(persona_path, "w", encoding="utf-8") as f:
        f.write(default)
    ok("persona.txt created")
    info(f"Edit {CYAN}persona.txt{RESET} to give the bot its personality")

# ── Step 5: directories ───────────────────────────────────────────────────────
section("5  Directories")
for d in ("contacts", "logs"):
    path = os.path.join(HERE, d)
    existed = os.path.isdir(path)
    os.makedirs(path, exist_ok=True)
    ok(f"{d}/  {'already exists' if existed else 'created'}")

# ── Step 6: ngrok ─────────────────────────────────────────────────────────────
section("6  Ngrok")
if shutil.which("ngrok"):
    ok("ngrok found in PATH")
else:
    fail("ngrok not found")
    errors.append("ngrok")
    if sys.platform == "win32":
        info(f"Install via winget:      {CYAN}winget install ngrok.ngrok{RESET}")
        info(f"Install via Chocolatey:  {CYAN}choco install ngrok{RESET}")
    else:
        info(f"Install via snap:        {CYAN}snap install ngrok{RESET}")
        info(f"Install via apt:         {CYAN}sudo apt install ngrok{RESET}")
    info(f"Or download from:        {CYAN}https://ngrok.com/download{RESET}")
    print()
    info("After installing, authenticate once:")
    print(f"    {CYAN}ngrok config add-authtoken <your-token>{RESET}")
    info("Get your token at: https://dashboard.ngrok.com/get-started/your-authtoken")

# ── Step 7: run health check ──────────────────────────────────────────────────
section("7  Health check")
check_script = os.path.join(HERE, "check_services.py")
if os.path.isfile(check_script):
    info("Running check_services.py ...\n")
    subprocess.run([sys.executable, check_script])
else:
    info("check_services.py not found — skipping")

# ── Done ──────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}{'─' * 48}{RESET}")
if errors:
    print(f"{BOLD}Setup mostly complete{RESET} — fix the items above, then:\n")
else:
    print(f"{BOLD}Setup complete!{RESET}  Next steps:\n")

print(f"  1.  Start the bot:       {CYAN}python app.py{RESET}")
print(f"  2.  Start ngrok:         {CYAN}ngrok http 5000{RESET}")
print(f"  3.  Copy the https URL ngrok gives you, append {CYAN}/sms{RESET},")
print(f"      and paste it as the inbound webhook URL in your Vonage dashboard.")
print(f"  4.  Check everything:    {CYAN}python check_services.py{RESET}")
print()
