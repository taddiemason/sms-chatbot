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

def choose(question, options):
    """Present a numbered menu and return the index of the chosen option."""
    print(f"\n  {BOLD}{question}{RESET}")
    for i, opt in enumerate(options, 1):
        print(f"  {CYAN}{i}{RESET}  {opt}")
    while True:
        try:
            raw = input(f"\n  {CYAN}?{RESET}  Enter number: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"  {RED}  Please enter a number between 1 and {len(options)}.{RESET}")

def yn(question, default_yes=False):
    """Ask a yes/no question and return bool."""
    hint = "[Y/n]" if default_yes else "[y/N]"
    try:
        raw = input(f"  {CYAN}?{RESET}  {question} {DIM}{hint}{RESET}: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(0)
    if not raw:
        return default_yes
    return raw in ("y", "yes")

def setup_ngrok_as_service():
    """Configure ngrok to survive terminal close by running it as a service."""

    # Locate ngrok's config file
    if sys.platform == "win32":
        config_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ngrok")
    else:
        config_dir = os.path.expanduser("~/.config/ngrok")
    config_path = os.path.join(config_dir, "ngrok.yml")

    # ── Authtoken ──────────────────────────────────────────────────────────────
    has_token = False
    if os.path.isfile(config_path):
        with open(config_path, encoding="utf-8") as f:
            has_token = "authtoken" in f.read()

    if has_token:
        ok("Ngrok authtoken already configured")
    else:
        info("An authtoken is required for ngrok to run as a service.")
        print(f"  {DIM}Get yours at: https://dashboard.ngrok.com/get-started/your-authtoken{RESET}")
        token = prompt("Ngrok authtoken")
        if not token:
            fail("Authtoken required — skipping ngrok service setup")
            errors.append("ngrok authtoken missing")
            return
        r = subprocess.run(["ngrok", "config", "add-authtoken", token],
                           capture_output=True, text=True)
        if r.returncode == 0:
            ok("Authtoken saved")
        else:
            fail("Failed to save authtoken: " + r.stderr.strip()[:80])
            errors.append("ngrok authtoken")
            return

    # ── Named tunnel in ngrok config ───────────────────────────────────────────
    config_text = ""
    if os.path.isfile(config_path):
        with open(config_path, encoding="utf-8") as f:
            config_text = f.read()

    if "sms-chatbot" in config_text:
        ok("Tunnel 'sms-chatbot' already in ngrok config")
    elif "tunnels:" in config_text:
        # A tunnels block exists but doesn't have our tunnel — show what to add
        info("Add this to your ngrok config manually under the existing tunnels: block:")
        print(f"\n    {CYAN}  sms-chatbot:\n    proto: http\n    addr: 5000{RESET}\n")
        print(f"  Config file: {CYAN}{config_path}{RESET}")
    else:
        tunnel_block = "\ntunnels:\n  sms-chatbot:\n    proto: http\n    addr: 5000\n"
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, "a", encoding="utf-8") as f:
            f.write(tunnel_block)
        ok("Tunnel 'sms-chatbot' added to ngrok config")

    # ── Service setup ──────────────────────────────────────────────────────────
    print()
    if sys.platform == "win32":
        info("Install ngrok as a Windows service (run the following as Administrator):")
        print(f"    {CYAN}ngrok service install{RESET}")
        print(f"    {CYAN}ngrok service start{RESET}")
        print()
        info(f"To check status:  {CYAN}ngrok service status{RESET}")
        info(f"To stop:          {CYAN}ngrok service stop{RESET}")
    else:
        ngrok_bin = shutil.which("ngrok") or "/usr/bin/ngrok"
        user = os.environ.get("USER", "root")
        service_content = (
            "[Unit]\n"
            "Description=Ngrok tunnel for SMS chatbot\n"
            "After=network.target\n\n"
            "[Service]\n"
            f"User={user}\n"
            f"ExecStart={ngrok_bin} start sms-chatbot\n"
            "Restart=always\n"
            "RestartSec=5\n\n"
            "[Install]\n"
            "WantedBy=multi-user.target\n"
        )
        ngrok_service_path = os.path.join(HERE, "ngrok.service")
        with open(ngrok_service_path, "w", encoding="utf-8") as f:
            f.write(service_content)
        ok(f"ngrok.service written to project directory")
        print()
        info("Install the ngrok service:")
        print(f"    {CYAN}sudo cp ngrok.service /etc/systemd/system/{RESET}")
        print(f"    {CYAN}sudo systemctl daemon-reload{RESET}")
        print(f"    {CYAN}sudo systemctl enable ngrok{RESET}")
        print(f"    {CYAN}sudo systemctl start ngrok{RESET}")
        print()
        info(f"To check status:  {CYAN}sudo systemctl status ngrok{RESET}")

errors = []

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}SMS Chatbot — Setup{RESET}")
print(f"{DIM}Installs dependencies and walks through all required configuration.{RESET}")

# ── Environment choice ────────────────────────────────────────────────────────
env_choice = choose(
    "Where are you setting this up?",
    [
        "Local machine  (development / testing — uses ngrok for the public URL)",
        "Homelab / Linux server  (production — uses gunicorn + systemd service)",
    ],
)
IS_LOCAL  = env_choice == 0
IS_SERVER = env_choice == 1

print()
if IS_LOCAL:
    info("Local setup selected — will use ngrok for the public webhook URL")
else:
    info("Server setup selected — will configure a virtualenv and systemd service")

# ── Step 1: Python version ────────────────────────────────────────────────────
section("1  Python version")
major, minor = sys.version_info[:2]
if (major, minor) < (3, 8):
    fail(f"Python 3.8+ required, found {major}.{minor}")
    sys.exit(1)
ok(f"Python {major}.{minor}")

# ── Step 2: Python packages ───────────────────────────────────────────────────
section("2  Python packages")
req = os.path.join(HERE, "requirements.txt")
if not os.path.isfile(req):
    fail("requirements.txt not found — are you in the right directory?")
    sys.exit(1)

if IS_SERVER:
    # Create a venv if one doesn't exist
    venv_path = os.path.join(HERE, "venv")
    if os.path.isdir(venv_path):
        ok("venv/ already exists")
    else:
        info("Creating virtual environment (venv/) ...")
        result = subprocess.run(
            [sys.executable, "-m", "venv", venv_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            fail("Failed to create venv:\n" + result.stderr)
            sys.exit(1)
        ok("venv/ created")

    # Use the venv's python -m pip rather than bin/pip — python is always present
    venv_python = os.path.join(venv_path, "bin", "python3")
    if not os.path.isfile(venv_python):
        venv_python = os.path.join(venv_path, "bin", "python")
    if not os.path.isfile(venv_python):
        venv_python = os.path.join(venv_path, "Scripts", "python.exe")  # Windows fallback

    info("Installing packages into venv ...")
    result = subprocess.run(
        [venv_python, "-m", "pip", "install", "-r", req, "--quiet"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail("pip install failed:\n" + result.stderr)
        sys.exit(1)
    ok("All packages installed into venv")

else:
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

# ── Step 5: directories & log files ──────────────────────────────────────────
section("5  Directories")
for d in ("contacts", "logs"):
    path = os.path.join(HERE, d)
    existed = os.path.isdir(path)
    os.makedirs(path, exist_ok=True)
    ok(f"{d}/  {'already exists' if existed else 'created'}")

for log_file in ("logs/chat.log", "logs/service.log"):
    log_path = os.path.join(HERE, log_file)
    if os.path.isfile(log_path):
        ok(f"{log_file}  already exists")
    else:
        open(log_path, "w").close()
        ok(f"{log_file}  created")

# ── Step 6: tunnel / public URL ───────────────────────────────────────────────
if IS_LOCAL:
    section("6  Ngrok")
    if shutil.which("ngrok"):
        ok("ngrok found in PATH")
        print()
        if yn("Set up ngrok to run as a background service so it keeps running after you close the terminal?"):
            setup_ngrok_as_service()
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
        info("After installing, re-run this script to set it up as a background service.")

else:
    section("6  Public URL (for Vonage webhooks)")
    info("Your server needs a stable public HTTPS URL so Vonage can reach it.")
    print()
    tunnel_choice = choose(
        "Which tunneling method will you use?",
        [
            "Cloudflare Tunnel  (recommended — free, stable domain, requires a domain on Cloudflare)",
            "Ngrok on the server  (simpler — free tier changes URL on restart)",
            "I already have a domain / reverse proxy set up",
        ],
    )

    if tunnel_choice == 0:
        print(f"""
  {BOLD}Cloudflare Tunnel setup:{RESET}

  {DIM}Install cloudflared:{RESET}
    {CYAN}curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared{RESET}
    {CYAN}chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/{RESET}

  {DIM}Authenticate and create the tunnel:{RESET}
    {CYAN}cloudflared tunnel login{RESET}
    {CYAN}cloudflared tunnel create sms-chatbot{RESET}

  {DIM}Create ~/.cloudflared/config.yml with:{RESET}
    tunnel: <YOUR-TUNNEL-UUID>
    credentials-file: /home/<user>/.cloudflared/<YOUR-TUNNEL-UUID>.json
    ingress:
      - hostname: yourdomain.com
        service: http://localhost:5000
      - service: http_status:404

  {DIM}Route and install as a service:{RESET}
    {CYAN}cloudflared tunnel route dns sms-chatbot yourdomain.com{RESET}
    {CYAN}sudo cloudflared service install{RESET}

  Your webhook URL will be: {CYAN}https://yourdomain.com/sms{RESET}
""")
    elif tunnel_choice == 1:
        if shutil.which("ngrok"):
            ok("ngrok found in PATH")
            print()
            setup_ngrok_as_service()
        else:
            fail("ngrok not found")
            errors.append("ngrok")
            info(f"Install via snap:   {CYAN}snap install ngrok{RESET}")
            info(f"Or download from:   {CYAN}https://ngrok.com/download{RESET}")
            print()
            info("After installing, re-run this script to finish ngrok service setup.")
    else:
        ok("Skipping tunnel setup — using existing domain/proxy")
        info("Make sure your reverse proxy forwards requests to port 5000")

    # ── Step 7: systemd service ───────────────────────────────────────────────
    section("7  Systemd service")
    service_src = os.path.join(HERE, "sms-chatbot.service")

    if not os.path.isfile(service_src):
        fail("sms-chatbot.service not found — skipping service setup")
        errors.append("sms-chatbot.service missing")
    else:
        # Detect the install path and venv gunicorn path to fill into the service file
        venv_gunicorn = os.path.join(HERE, "venv", "bin", "gunicorn")
        print()
        info("The service file needs to know where the project lives on this server.")
        info(f"Detected path: {CYAN}{HERE}{RESET}")
        confirmed_path = prompt("Project path", default=HERE)
        confirmed_path = confirmed_path.rstrip("/")

        with open(service_src, encoding="utf-8") as f:
            service_content = f.read()

        venv_gunicorn_final = os.path.join(confirmed_path, "venv", "bin", "gunicorn")
        service_content = service_content.replace("/path/to/sms-chatbot", confirmed_path)
        service_content = service_content.replace(
            "/home/youruser/sms-chatbot/venv/bin/gunicorn", venv_gunicorn_final
        )

        configured_service = os.path.join(HERE, "sms-chatbot.service.configured")
        with open(configured_service, "w", encoding="utf-8") as f:
            f.write(service_content)

        ok(f"Configured service file written to {os.path.basename(configured_service)}")
        print()
        info("Install and enable the service:")
        print(f"    {CYAN}sudo cp sms-chatbot.service.configured /etc/systemd/system/sms-chatbot.service{RESET}")
        print(f"    {CYAN}sudo systemctl daemon-reload{RESET}")
        print(f"    {CYAN}sudo systemctl enable sms-chatbot{RESET}")
        print(f"    {CYAN}sudo systemctl start sms-chatbot{RESET}")
        print(f"    {CYAN}sudo systemctl status sms-chatbot{RESET}")

# ── Step 7/8: health check ────────────────────────────────────────────────────
health_step = "8" if IS_SERVER else "7"
section(f"{health_step}  Health check")
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

if IS_LOCAL:
    print(f"  1.  Start the bot:       {CYAN}python app.py{RESET}")
    print(f"  2.  Start ngrok:")
    print(f"        As a service:      {CYAN}ngrok service start{RESET}  (if you set it up above)")
    print(f"        Or manually:       {CYAN}ngrok http 5000{RESET}")
    print(f"  3.  Copy the https URL ngrok gives you, append {CYAN}/sms{RESET},")
    print(f"      and paste it as the inbound webhook URL in your Vonage dashboard.")
    print(f"  4.  Check everything:    {CYAN}python check_services.py{RESET}")
else:
    print(f"  1.  Install the service (commands printed above)")
    print(f"  2.  Start the service:   {CYAN}sudo systemctl start sms-chatbot{RESET}")
    print(f"  3.  Set the Vonage inbound webhook URL to your public URL + {CYAN}/sms{RESET}")
    print(f"  4.  Check everything:    {CYAN}python check_services.py{RESET}")
print()
