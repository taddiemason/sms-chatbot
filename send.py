import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

def send_sms(to: str, body: str) -> None:
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    message = client.messages.create(
        from_=os.environ["TWILIO_PHONE_NUMBER"],
        to=to,
        body=body,
    )
    print(f"Sent to {to}: {body}")
    print(f"Message SID: {message.sid}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('Usage: python send.py "+1234567890" "Your message here"')
        sys.exit(1)
    send_sms(sys.argv[1], sys.argv[2])
