# Troubleshooting

Run the health check first — it identifies most issues automatically:

```bash
cd ~/sms-chatbot
source venv/bin/activate
python check_services.py
```

---

## Bot not responding to texts

**1. Check the health check passes 16/16.**
Any failing check is a direct cause.

**2. Verify the Vonage webhook URL is correct.**
Go to **Vonage Dashboard → Build & Manage → Numbers → Your Numbers**, click the gear icon, and confirm the Inbound Webhook URL is set to your current ngrok/Cloudflare URL + `/sms`, e.g.:
```
https://abc123.ngrok-free.dev/sms
```
The HTTP Method must be `POST-Form`.

**3. Check if the bot is actually receiving the request.**
```bash
tail -f ~/sms-chatbot/logs/chat.log
```
Send a text and watch for a `[IN]` line. If nothing appears, Vonage isn't reaching the webhook — the URL is wrong or ngrok/the tunnel is down.

**4. Check for errors in the service log.**
```bash
sudo journalctl -u sms-chatbot -n 50
# or
tail -f ~/sms-chatbot/logs/service.log
```

---

## Service won't start or keeps crashing

**Check the service status and recent logs:**
```bash
sudo systemctl status sms-chatbot
sudo journalctl -u sms-chatbot -n 50
```

**Common causes:**

| Symptom in logs | Fix |
|---|---|
| `KeyError: 'VONAGE_API_KEY'` | `.env` file is missing or not loaded — check `EnvironmentFile=` path in the service file |
| `ModuleNotFoundError` | Wrong Python/gunicorn in service file — confirm `ExecStart` points to `venv/bin/gunicorn` |
| `Address already in use` | Another process is on port 5000 — run `sudo lsof -i :5000` to find and kill it |
| `Permission denied` | Service `User=` doesn't have read access to the project directory |

**Verify the service file paths are correct:**
```bash
cat /etc/systemd/system/sms-chatbot.service
```
`WorkingDirectory`, `EnvironmentFile`, and `ExecStart` must all point to real paths. If you moved the project, re-run `python install.py --reconfigure`.

**Restart after any fix:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart sms-chatbot
sudo systemctl status sms-chatbot
```

---

## Ngrok tunnel is down

**Check if ngrok is running:**
```bash
sudo systemctl status ngrok
curl -s http://127.0.0.1:4040/api/tunnels
```

**Restart the ngrok service:**
```bash
sudo systemctl restart ngrok
sudo systemctl status ngrok
```

**Get the current public URL** (free tier URL changes on restart):
```bash
curl -s http://127.0.0.1:4040/api/tunnels | python3 -m json.tool
```
Copy the `https://` URL, append `/sms`, and update the Vonage webhook URL.

**Ngrok service fails to start — "Tunnel 'sms-chatbot' is not defined":**
If ngrok was installed via snap, it reads config from a different path than the standard one.
Check which config file ngrok actually uses:
```bash
ngrok config check
# or run any ngrok command and look for "Config files read: [...]"
```
Then add the tunnel to that file (replace the path with what ngrok reported):
```bash
cat >> ~/snap/ngrok/current/.config/ngrok/ngrok.yml << 'EOF'

tunnels:
  sms-chatbot:
    proto: http
    addr: 5000
EOF
sudo systemctl restart ngrok
```

**Ngrok service fails to start — other errors:**
Check that the authtoken and tunnel config are saved:
```bash
cat ~/.config/ngrok/ngrok.yml          # standard install
cat ~/snap/ngrok/current/.config/ngrok/ngrok.yml  # snap install
```
It should contain `authtoken:` and a `tunnels:` block with `sms-chatbot`. If missing, re-run `python install.py --reconfigure` and choose the ngrok option.

**Free tier URL keeps changing on restart:**
This is a limitation of the free tier. Options:
- Upgrade to a paid ngrok plan for a fixed domain
- Switch to Cloudflare Tunnel (free, requires a domain)
- Re-run `python install.py --reconfigure` and choose Cloudflare Tunnel

---

## API credential errors

**Groq authentication failed:**
1. Check `GROQ_API_KEY` in `.env` starts with `gsk_`
2. Verify the key is still active at [console.groq.com](https://console.groq.com) → API Keys
3. Update `.env` and restart: `sudo systemctl restart sms-chatbot`

**Vonage authentication failed:**
1. Check `VONAGE_API_KEY` and `VONAGE_API_SECRET` in `.env`
2. Find current values at [dashboard.nexmo.com](https://dashboard.nexmo.com) → top of main page
3. Update `.env` and restart: `sudo systemctl restart sms-chatbot`

**Edit `.env` directly:**
```bash
nano ~/sms-chatbot/.env
sudo systemctl restart sms-chatbot
```

---

## Python packages not found

**If running manually** (not as a service), make sure the venv is activated:
```bash
source ~/sms-chatbot/venv/bin/activate
python check_services.py
```

**Reinstall packages into the venv:**
```bash
cd ~/sms-chatbot
source venv/bin/activate
pip install -r requirements.txt
```

**If the venv is broken**, recreate it:
```bash
cd ~/sms-chatbot
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sms-chatbot
```

---

## Bot replies with "Sorry, I'm having trouble right now"

This means the Groq API call failed. Check the log:
```bash
grep "\[ERR\]" ~/sms-chatbot/logs/chat.log | tail -20
```

Common causes:
- Invalid or expired `GROQ_API_KEY`
- Groq rate limit hit (free tier has limits — wait a minute and try again)
- No internet connectivity from the server: `curl -I https://api.groq.com`

---

## Vonage sends an error / SMS not delivered

Check for `[SEND_ERR]` lines in the log:
```bash
grep "SEND_ERR" ~/sms-chatbot/logs/chat.log | tail -20
```

Common causes:
- `VONAGE_PHONE_NUMBER` is in the wrong format — must be E.164 with `+` prefix, e.g. `+15551234567`
- Insufficient Vonage account balance — check at [dashboard.nexmo.com](https://dashboard.nexmo.com)
- Sending to a number in a country your Vonage number doesn't support

---

## Everything was working, then stopped after a reboot

Services aren't set to start on boot. Check:
```bash
sudo systemctl is-enabled sms-chatbot
sudo systemctl is-enabled ngrok
```
If either returns `disabled`:
```bash
sudo systemctl enable sms-chatbot
sudo systemctl enable ngrok
sudo systemctl start sms-chatbot
sudo systemctl start ngrok
```

---

## Useful log commands

```bash
# Live conversation log
tail -f ~/sms-chatbot/logs/chat.log

# All messages from a specific number
grep "+15551234567" ~/sms-chatbot/logs/chat.log

# All errors
grep -E "\[ERR\]|\[SEND_ERR\]|\[WEBHOOK\]" ~/sms-chatbot/logs/chat.log

# Service startup log
tail -f ~/sms-chatbot/logs/service.log

# Systemd journal (bot service)
sudo journalctl -u sms-chatbot -f

# Systemd journal (ngrok service)
sudo journalctl -u ngrok -f
```
