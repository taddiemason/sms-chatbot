import os
import logging

from vonage import Auth, Vonage
from vonage_sms import SmsMessage

from channels.base import Messenger

log = logging.getLogger("smsbot")


class VonageMessenger(Messenger):
    """Outbound SMS via the Vonage REST API."""

    name = "sms"

    def __init__(self):
        self._client = Vonage(Auth(
            api_key=os.environ["VONAGE_API_KEY"],
            api_secret=os.environ["VONAGE_API_SECRET"],
        ))
        self._from = os.environ["VONAGE_PHONE_NUMBER"].lstrip("+")

    def send(self, to: str, text: str) -> None:
        response = self._client.sms.send(SmsMessage(
            to=to.lstrip("+"),
            from_=self._from,
            text=text,
        ))
        msg_result = response.messages[0]
        if msg_result.status != "0":
            log.error(f"[SEND_ERR] Vonage error for {to}: status={msg_result.status} error={msg_result.error_text}")
        else:
            log.info(f"[SENT] {to}: {text}")
