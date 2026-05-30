import time
from config import MAX_HISTORY_MESSAGES, CONVERSATION_EXPIRY_HOURS


class ConversationHistory:
    def __init__(self):
        self._history: dict[str, list[dict]] = {}
        self._last_active: dict[str, float] = {}

    def add(self, number: str, role: str, content: str) -> None:
        if number not in self._history:
            self._history[number] = []
        self._last_active[number] = time.time()
        self._history[number].append({"role": role, "content": content})
        if len(self._history[number]) > MAX_HISTORY_MESSAGES:
            self._history[number] = self._history[number][-MAX_HISTORY_MESSAGES:]

    def get(self, number: str) -> list[dict]:
        if number in self._last_active:
            elapsed_hours = (time.time() - self._last_active[number]) / 3600
            if elapsed_hours >= CONVERSATION_EXPIRY_HOURS:
                print(f"[EXPIRED] Clearing stale history for {number}")
                self.clear(number)
        return self._history.get(number, [])

    def clear(self, number: str) -> None:
        self._history.pop(number, None)
        self._last_active.pop(number, None)
