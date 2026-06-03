import os
import hmac
import hashlib
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort, jsonify

load_dotenv()

# Imported after load_dotenv() — brain and the messenger read env vars at import/init.
from config import ALLOWED_NUMBERS
from channels.vonage_sms import VonageMessenger
import brain

log = logging.getLogger("smsbot")

app = Flask(__name__)
messenger = VonageMessenger()


@app.route("/sms", methods=["POST"])
def sms_reply():
    # Vonage sends form-encoded POST; fall back to JSON if needed
    params = request.form.to_dict() if request.form else request.json or {}

    # Optional webhook signature verification (requires VONAGE_SIGNATURE_SECRET)
    sig_secret = os.environ.get("VONAGE_SIGNATURE_SECRET", "")
    if sig_secret:
        sig = params.pop("sig", "")
        sorted_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        expected = hmac.new(sig_secret.encode(), sorted_str.encode(), hashlib.md5).hexdigest()
        if not hmac.compare_digest(sig.lower(), expected.lower()):
            log.error("[WEBHOOK] Signature validation failed")
            abort(403)

    raw_from = params.get("msisdn") or params.get("from", "")
    from_number = "+" + raw_from.lstrip("+")
    user_message = (params.get("text") or "").strip()

    if ALLOWED_NUMBERS and from_number not in ALLOWED_NUMBERS:
        return jsonify({}), 200

    brain.process_message(messenger, from_number, user_message)

    # Respond to Vonage immediately — actual SMS sent via REST in a background thread
    return jsonify({}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
