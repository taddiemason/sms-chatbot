import os
import time
import random
import threading
from dotenv import load_dotenv
from flask import Flask, request, abort
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient
from twilio.request_validator import RequestValidator
from werkzeug.middleware.proxy_fix import ProxyFix
from groq import Groq

from config import (
    SYSTEM_PROMPT, GROQ_MODEL, ALLOWED_NUMBERS, MAX_TOKENS,
    TYPING_SPEED_WPM, TYPING_JITTER_FRACTION, TYPING_DELAY_MIN, TYPING_DELAY_MAX,
    AUTO_UPDATE_CONTACTS,
)
from conversation import ConversationHistory
import profiles

load_dotenv()

app = Flask(__name__)
# Lets Flask see the real HTTPS URL when behind ngrok or a reverse proxy,
# which is required for Twilio signature validation to work.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
twilio_client = TwilioClient(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
twilio_phone = os.environ["TWILIO_PHONE_NUMBER"]
validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])
history = ConversationHistory()

# Load bot persona once at startup; fall back to config SYSTEM_PROMPT if file is missing
BOT_PERSONA = profiles.load_persona() or SYSTEM_PROMPT
print(f"[PERSONA] Loaded: {BOT_PERSONA[:80]}{'...' if len(BOT_PERSONA) > 80 else ''}")


def _build_system_content(number: str) -> str:
    contact = profiles.load_contact(number)
    content = BOT_PERSONA
    if contact:
        content += f"\n\nWhat you know about this person:\n{contact}"
    return content


def _send_and_update(to_number: str, message: str, delay: float,
                     user_message: str, ai_reply: str) -> None:
    time.sleep(delay)
    twilio_client.messages.create(body=message, from_=twilio_phone, to=to_number)
    print(f"[SENT] {to_number}: {message[:60]}{'...' if len(message) > 60 else ''}")

    if AUTO_UPDATE_CONTACTS:
        profiles.update_contact(to_number, user_message, ai_reply, groq_client)


@app.route("/sms", methods=["POST"])
def sms_reply():
    # Reject requests not signed by Twilio (prevents spoofed webhooks)
    signature = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(request.url, request.form, signature):
        abort(403)

    from_number = request.form.get("From", "")
    user_message = request.form.get("Body", "").strip()

    if ALLOWED_NUMBERS and from_number not in ALLOWED_NUMBERS:
        return str(MessagingResponse())

    if not user_message:
        return str(MessagingResponse())

    # Let user wipe their conversation history
    if user_message.lower() == "reset":
        history.clear(from_number)
        print(f"[RESET] {from_number}")
        t = threading.Thread(
            target=_send_and_update,
            args=(from_number, "Conversation cleared. Starting fresh!", TYPING_DELAY_MIN, "", ""),
            daemon=True,
        )
        t.start()
        return str(MessagingResponse())

    print(f"[IN]  {from_number}: {user_message}")
    history.add(from_number, "user", user_message)

    system_content = _build_system_content(from_number)
    messages = [{"role": "system", "content": system_content}] + history.get(from_number)

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
        )
        ai_reply = completion.choices[0].message.content
        history.add(from_number, "assistant", ai_reply)
    except Exception as e:
        print(f"[ERR] Groq error for {from_number}: {e}")
        ai_reply = "Sorry, I'm having trouble right now. Try again in a moment."
        user_message = ""  # don't try to extract facts from a failed exchange

    word_count = len(ai_reply.split())
    delay = (word_count / TYPING_SPEED_WPM) * 60
    jitter = delay * TYPING_JITTER_FRACTION * random.uniform(-1, 1)
    delay = max(TYPING_DELAY_MIN, min(TYPING_DELAY_MAX, delay + jitter))
    print(f"[OUT] {from_number} in {delay:.1f}s: {ai_reply[:60]}{'...' if len(ai_reply) > 60 else ''}")

    # Send after delay in background; also runs contact auto-update after sending
    t = threading.Thread(
        target=_send_and_update,
        args=(from_number, ai_reply, delay, user_message, ai_reply),
        daemon=True,
    )
    t.start()

    # Respond to Twilio immediately with empty TwiML (actual SMS sent via REST above)
    return str(MessagingResponse())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
