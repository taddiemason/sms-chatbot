import time
import logging

import requests

from channels.base import Messenger

log = logging.getLogger("smsbot")

_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramMessenger(Messenger):
    """Outbound + inbound via the Telegram Bot API.

    Needs no phone number and no public webhook — `poll()` long-polls Telegram's
    servers for incoming messages. The bot can only message a user after that user
    has pressed Start (which is how we first learn their chat id).
    """

    name = "telegram"

    def __init__(self, token: str):
        self._token = token

    def _url(self, method: str) -> str:
        return _API.format(token=self._token, method=method)

    def send(self, to: str, text: str) -> None:
        try:
            resp = requests.post(
                self._url("sendMessage"),
                json={"chat_id": to, "text": text},
                timeout=30,
            )
            data = resp.json()
            if not data.get("ok"):
                log.error(f"[SEND_ERR] Telegram error for {to}: {data.get('description')}")
            else:
                log.info(f"[SENT] {to}: {text}")
        except requests.exceptions.RequestException as e:
            log.error(f"[SEND_ERR] Telegram request failed for {to}: {e}")

    def get_me(self) -> dict:
        """Return Telegram's getMe response (used to validate the token)."""
        return requests.get(self._url("getMe"), timeout=10).json()

    def poll(self, handler) -> None:
        """Long-poll getUpdates forever; call handler(chat_id: str, text: str) per text message."""
        offset = None
        log.info("[TELEGRAM] Long-polling started")
        while True:
            try:
                params = {"timeout": 30}
                if offset is not None:
                    params["offset"] = offset
                resp = requests.get(self._url("getUpdates"), params=params, timeout=40)
                data = resp.json()
                if not data.get("ok"):
                    log.error(f"[TELEGRAM] getUpdates error: {data.get('description')}")
                    time.sleep(5)
                    continue
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message") or update.get("edited_message")
                    if not message:
                        continue
                    text = (message.get("text") or "").strip()
                    chat_id = message.get("chat", {}).get("id")
                    if chat_id is None or not text:
                        continue
                    try:
                        handler(str(chat_id), text)
                    except Exception as e:
                        log.error(f"[TELEGRAM] handler error for {chat_id}: {e}")
            except requests.exceptions.RequestException as e:
                log.error(f"[TELEGRAM] poll request failed: {e}")
                time.sleep(5)
