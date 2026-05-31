import time
import logging
import threading
from config import MAX_HISTORY_MESSAGES, CONVERSATION_EXPIRY_HOURS

log = logging.getLogger("smsbot")


class ConversationHistory:
    def __init__(self):
        self._history: dict[str, list[dict]] = {}
        self._last_active: dict[str, float] = {}
        self._lock = threading.Lock()

    def add(self, number: str, role: str, content: str) -> None:
        with self._lock:
            if number not in self._history:
                self._history[number] = []
            self._last_active[number] = time.time()
            self._history[number].append({"role": role, "content": content})
            if len(self._history[number]) > MAX_HISTORY_MESSAGES:
                self._history[number] = self._history[number][-MAX_HISTORY_MESSAGES:]

    def get(self, number: str) -> list[dict]:
        with self._lock:
            if number in self._last_active:
                elapsed_hours = (time.time() - self._last_active[number]) / 3600
                if elapsed_hours >= CONVERSATION_EXPIRY_HOURS:
                    log.info(f"[EXPIRED] Clearing stale history for {number}")
                    self._clear_locked(number)
            return list(self._history.get(number, []))

    def clear(self, number: str) -> None:
        with self._lock:
            self._clear_locked(number)

    def _clear_locked(self, number: str) -> None:
        self._history.pop(number, None)
        self._last_active.pop(number, None)
