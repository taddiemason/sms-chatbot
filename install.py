#!/usr/bin/env python3
"""One-time setup script — installs dependencies and walks through configuration."""

import os
import re
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

TOTAL_STEPS = 8  # overridden after IS_LOCAL/IS_SERVER are set
_step = 0

def section(title):
    global _step
    _step += 1
    label = f"Step {_step} of {TOTAL_STEPS}  {title}"
    print(f"\n{BOLD}{CYAN}── {label} {'─' * max(1, 44 - len(label))}{RESET}")

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

def validate_credential(key, value):
    """Returns (is_valid: bool, message: str). Called after packages are installed."""
    if key == "GROQ_API_KEY":
        if not value.startswith("gsk_"):
            return False, "Groq API keys must start with 'gsk_'"
        try:
            from groq import Groq
            Groq(api_key=value).models.list()
            return True, "Groq API key validated"
        except Exception as e:
            msg = str(e)
            if "401" in msg or "auth" in msg.lower() or "invalid" in msg.lower():
                return False, "Groq rejected this key — check console.groq.com"
            return True, f"Could not reach Groq to verify (network: {msg[:60]}) — accepted"

    if key == "VONAGE_API_KEY":
        if not re.fullmatch(r"[a-zA-Z0-9]{8}", value):
            return False, "Vonage API key must be exactly 8 alphanumeric characters"
        return True, ""

    if key == "VONAGE_API_SECRET":
        if len(value) < 16:
            return False, f"Vonage API secret looks too short ({len(value)} chars, expected ≥16)"
        return True, ""

    if key == "VONAGE_PHONE_NUMBER":
        if not re.fullmatch(r'\+\d{10,15}', value):
            return False, "Must be E.164 format: + followed by 10–15 digits (e.g. +15551234567)"
        return True, ""

    return True, ""

def setup_ngrok_as_service():
    """Configure ngrok to survive terminal close by running it as a service."""

    # Locate ngrok's config file.
    # Snap-installed ngrok reads from ~/snap/ngrok/current/.config/ngrok/ngrok.yml,
    # not ~/.config/ngrok/ngrok.yml — detect this by asking ngrok itself.
    def _ngrok_config_path():
        if sys.platform == "win32":
            return os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ngrok", "ngrok.yml"
            )
        # Ask ngrok which config files it reads
        r = subprocess.run(["ngrok", "config", "check"],
                           capture_output=True, text=True)
        for line in (r.stdout + r.stderr).splitlines():
            if "ngrok.yml" in line:
                # Extract the path from lines like "Valid configuration file at /path/ngrok.yml"
                # or the error output "Config files read: [/path/ngrok.yml]"
                m = re.search(r'(/[^\s\]]+ngrok\.yml)', line)
                if m:
                    return m.group(1)
        # Fallback to standard XDG path
        return os.path.expanduser("~/.config/ngrok/ngrok.yml")

    config_path = _ngrok_config_path()
    config_dir  = os.path.dirname(config_path)

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
venv_python = sys.executable  # overridden to venv python on server path

RECONFIGURE = "--reconfigure" in sys.argv

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

TOTAL_STEPS = 8 if IS_LOCAL else 9

# ── Re-run detection: skip straight to health check if already configured ─────
if not RECONFIGURE:
    env_path_check = os.path.join(HERE, ".env")
    required_keys  = {"VONAGE_API_KEY", "VONAGE_API_SECRET", "VONAGE_PHONE_NUMBER", "GROQ_API_KEY"}
    existing_keys  = set()
    if os.path.isfile(env_path_check):
        with open(env_path_check, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    if v.strip():
                        existing_keys.add(k.strip())

    venv_ok    = not IS_SERVER or os.path.isdir(os.path.join(HERE, "venv"))
    env_ok     = required_keys.issubset(existing_keys)
    persona_ok = os.path.isfile(os.path.join(HERE, "persona.txt"))

    if venv_ok and env_ok and persona_ok:
        print(f"\n  {GREEN}Looks like setup is already complete — skipping to health check.{RESET}")
        print(f"  {DIM}Run with --reconfigure to redo all steps.{RESET}")
        if IS_SERVER:
            venv_path   = os.path.join(HERE, "venv")
            venv_python = os.path.join(venv_path, "bin", "python3")
            if not os.path.isfile(venv_python):
                venv_python = os.path.join(venv_path, "bin", "python")
        check_script = os.path.join(HERE, "check_services.py")
        if os.path.isfile(check_script):
            print()
            subprocess.run([venv_python, check_script])
        sys.exit(0)

# ── Step 1: Python version ────────────────────────────────────────────────────
section("Python version")
major, minor = sys.version_info[:2]
if (major, minor) < (3, 8):
    fail(f"Python 3.8+ required, found {major}.{minor}")
    sys.exit(1)
ok(f"Python {major}.{minor}")

# ── Step 2: Python packages ───────────────────────────────────────────────────
section("Python packages")
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
    # Also update module-level venv_python so health check runs inside the venv
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
section("Environment variables  (.env)")

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
        if not val:
            if not required:
                return
            print(f"  {RED}  Required — please enter a value.{RESET}")
            continue
        is_valid, msg = validate_credential(key, val)
        if is_valid:
            if msg:
                ok(msg)
            values[key] = val
            return
        else:
            fail(msg)
            if not yn("Try again?", default_yes=True):
                info("Accepted as-is. Fix later with: python install.py --reconfigure")
                values[key] = val
                return

print(f"  {BOLD}Vonage credentials{RESET}")
print(f"  {DIM}No account yet? Sign up free at:  {CYAN}https://www.vonage.com/communications-apis/{RESET}")
print(f"  {DIM}Find your key and secret at:       {CYAN}https://dashboard.nexmo.com/getting-started/api-credentials{RESET}")
print()
collect("VONAGE_API_KEY",       "Vonage API key  (8 alphanumeric characters)")
collect("VONAGE_API_SECRET",    "Vonage API secret  (16+ characters)")

# Validate key+secret pair together via a live API call
_vk, _vs = values.get("VONAGE_API_KEY", ""), values.get("VONAGE_API_SECRET", "")
if _vk and _vs:
    while True:
        try:
            from vonage import Auth, Vonage
            _bal = Vonage(Auth(api_key=_vk, api_secret=_vs)).account.get_balance()
            ok(f"Vonage credentials verified  (account balance: {_bal.value:.4f})")
            break
        except Exception as _e:
            _m = str(_e)
            if "401" in _m or "auth" in _m.lower() or "invalid" in _m.lower():
                fail("Vonage authentication failed — API key or secret is incorrect")
                if yn("Re-enter Vonage credentials?", default_yes=True):
                    values.pop("VONAGE_API_KEY", None)
                    values.pop("VONAGE_API_SECRET", None)
                    collect("VONAGE_API_KEY",    "Vonage API key  (8 alphanumeric characters)")
                    collect("VONAGE_API_SECRET", "Vonage API secret  (16+ characters)")
                    _vk = values.get("VONAGE_API_KEY", "")
                    _vs = values.get("VONAGE_API_SECRET", "")
                else:
                    info("Continuing with unverified credentials")
                    break
            else:
                info(f"Could not reach Vonage to verify (network: {_m[:60]}) — continuing")
                break

collect("VONAGE_PHONE_NUMBER",  "Vonage phone number  (E.164 format, e.g. +15551234567)")
print()
print(f"  {BOLD}Groq API key{RESET}")
print(f"  {DIM}No account yet? Sign up free at:  {CYAN}https://console.groq.com{RESET}")
print()
collect("GROQ_API_KEY",         "Groq API key  (starts with gsk_)")
print()
print(f"  {DIM}Optional — enables HMAC signature verification on incoming webhooks{RESET}")
collect("VONAGE_SIGNATURE_SECRET", "Vonage signature secret", required=False)

with open(env_path, "w", encoding="utf-8") as f:
    for k, v in values.items():
        f.write(f"{k}={v}\n")
ok(".env saved")

# ── Step 4: persona.txt ───────────────────────────────────────────────────────
section("Bot persona  (persona.txt)")

persona_path = os.path.join(HERE, "persona.txt")
if os.path.isfile(persona_path):
    ok("persona.txt already exists")
else:
    info("No persona.txt found")
    print()
    if yn("Customize the bot persona now?", default_yes=False):
        print(f"  {DIM}Press Enter to accept the default shown in brackets.{RESET}\n")
        bot_name        = prompt("Bot name",                default="Alex")
        bot_age         = prompt("Bot age",                 default="26")
        bot_job         = prompt("Bot occupation",          default="personal assistant")
        bot_personality = prompt("Personality description", default="warm, witty, and direct")
        persona_text = (
            f"Your name is {bot_name}. You are {bot_age} years old"
            f" and work as a {bot_job}.\n"
            f"You are {bot_personality}.\n"
            "Communicate casually over text — no corporate tone, no stiff language.\n"
            "Never use markdown formatting like ** or # since it won't render in SMS.\n"
            "Keep replies short and natural since this is SMS, but be personal and genuine.\n"
            "If you already know the person's name, use it occasionally to feel more personal.\n"
        )
        ok(f"persona.txt created for '{bot_name}'")
    else:
        persona_text = (
            "You are a friendly and helpful assistant communicating over SMS.\n"
            "Keep replies concise and clear — SMS has limited space.\n"
            "Never use markdown formatting like ** or # since it won't render in SMS.\n"
        )
        ok("persona.txt created with default persona")
        info(f"Edit {CYAN}persona.txt{RESET} any time to change the bot's personality")
    with open(persona_path, "w", encoding="utf-8") as f:
        f.write(persona_text)

# ── Step 5: directories & log files ──────────────────────────────────────────
section("Directories")
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
    section("Ngrok")
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
    section("Public URL (for Vonage webhooks)")
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
    section("Systemd service")
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
        if yn("Install and start the sms-chatbot service now? (requires sudo)"):
            cmds = [
                ["sudo", "cp", configured_service, "/etc/systemd/system/sms-chatbot.service"],
                ["sudo", "systemctl", "daemon-reload"],
                ["sudo", "systemctl", "enable", "sms-chatbot"],
                ["sudo", "systemctl", "start",  "sms-chatbot"],
            ]
            all_ok = True
            for cmd in cmds:
                r = subprocess.run(cmd)
                if r.returncode != 0:
                    fail(f"Command failed: {' '.join(cmd)}")
                    all_ok = False
                    break
            if all_ok:
                ok("sms-chatbot service installed and started")
            else:
                info("Run these manually to finish:")
                print(f"    {CYAN}sudo cp sms-chatbot.service.configured /etc/systemd/system/sms-chatbot.service{RESET}")
                print(f"    {CYAN}sudo systemctl daemon-reload{RESET}")
                print(f"    {CYAN}sudo systemctl enable sms-chatbot{RESET}")
                print(f"    {CYAN}sudo systemctl start sms-chatbot{RESET}")
        else:
            info("Run these to install the service manually:")
            print(f"    {CYAN}sudo cp sms-chatbot.service.configured /etc/systemd/system/sms-chatbot.service{RESET}")
            print(f"    {CYAN}sudo systemctl daemon-reload{RESET}")
            print(f"    {CYAN}sudo systemctl enable sms-chatbot{RESET}")
            print(f"    {CYAN}sudo systemctl start sms-chatbot{RESET}")
            print(f"    {CYAN}sudo systemctl status sms-chatbot{RESET}")

# ── Webhook configuration guidance ───────────────────────────────────────────
section("Configure Vonage webhook")
print(f"""
  {BOLD}The bot only receives texts if Vonage knows where to forward them.{RESET}
  Here's exactly what to do — takes about 2 minutes:

  1. Open:   {CYAN}https://dashboard.nexmo.com/your-numbers{RESET}
  2. Find your Vonage number and click the {CYAN}gear icon ⚙{RESET} (Settings)
  3. Under 'Messages', set {CYAN}Inbound webhook URL{RESET} to:""")

if IS_LOCAL:
    print(f"""
        {CYAN}https://<YOUR-NGROK-URL>.ngrok-free.app/sms{RESET}
     (Start ngrok first, then run {CYAN}python check_services.py{RESET} to get your live URL)
""")
else:
    _domain = prompt("Your public domain (used in the instructions below)", default="yourdomain.com")
    print(f"""
        {CYAN}https://{_domain}/sms{RESET}
""")

print(f"  4. Set {CYAN}HTTP method{RESET} to POST")
print(f"  5. Click {CYAN}Save changes{RESET}")
print()
info(f"Confirm your setup any time: {CYAN}python check_services.py{RESET}")

# ── Health check ─────────────────────────────────────────────────────────────
section("Health check")
check_script = os.path.join(HERE, "check_services.py")
if os.path.isfile(check_script):
    info("Running check_services.py ...\n")
    subprocess.run([venv_python, check_script])
else:
    info("check_services.py not found — skipping")

# ── Done ──────────────────────────────────────────────────────────────────────
ERROR_FIXES = {
    "ngrok": (
        f"Install: {CYAN}snap install ngrok{RESET}  OR  {CYAN}https://ngrok.com/download{RESET}\n"
        f"       Then re-run: {CYAN}python install.py --reconfigure{RESET}"
    ),
    "ngrok authtoken missing": (
        f"Run: {CYAN}ngrok config add-authtoken <YOUR_TOKEN>{RESET}\n"
        f"       Get yours: {CYAN}https://dashboard.ngrok.com/get-started/your-authtoken{RESET}"
    ),
    "ngrok authtoken": (
        f"Run: {CYAN}ngrok config add-authtoken <YOUR_TOKEN>{RESET}\n"
        f"       Get yours: {CYAN}https://dashboard.ngrok.com/get-started/your-authtoken{RESET}"
    ),
    "sms-chatbot.service missing": (
        "The service template is missing from the project directory.\n"
        "       Re-clone the repo or download sms-chatbot.service from GitHub."
    ),
}
DEFAULT_FIX = f"Re-run setup: {CYAN}python install.py --reconfigure{RESET}"

print(f"\n{BOLD}{'─' * 48}{RESET}")
if errors:
    print(f"{BOLD}Setup mostly complete{RESET} — fix the item(s) below:\n")
    for err in errors:
        fix = ERROR_FIXES.get(err, DEFAULT_FIX)
        print(f"  {RED}✗{RESET}  {err}")
        print(f"       {YELLOW}Fix:{RESET} {fix}\n")
else:
    print(f"{BOLD}Setup complete!{RESET}  Next steps:\n")

if IS_LOCAL:
    print(f"  1.  Start the bot:        {CYAN}python app.py{RESET}")
    print(f"  2.  Start ngrok:")
    print(f"        As a service:       {CYAN}ngrok service start{RESET}  (if configured above)")
    print(f"        Or manually:        {CYAN}ngrok http 5000{RESET}")
    print(f"  3.  Get your webhook URL: {CYAN}python check_services.py{RESET}")
    print(f"        Then paste <ngrok-url>/sms into the Vonage dashboard (see Step 7 above)")
    print(f"  4.  Text your Vonage number — the bot should reply")
else:
    print(f"  1.  Install/start the service (commands printed above)")
    print(f"  2.  Paste your webhook URL into the Vonage dashboard (see Step 8 above)")
    print(f"  3.  Verify:               {CYAN}python check_services.py{RESET}")
    print(f"  4.  Text your Vonage number — the bot should reply")
print()
