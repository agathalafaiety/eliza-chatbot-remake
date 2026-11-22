"""Cotas compartilhadas pelas sessões de um processo Streamlit."""

from collections import deque
from threading import Lock
from time import monotonic

SESSION_LIMIT = 10
MINUTE_LIMIT = 5
DAILY_LIMIT = 50
DAY_SECONDS = 24 * 60 * 60


class RequestBudget:
    def __init__(self) -> None:
        self._attempts: deque[float] = deque()
        self._lock = Lock()

    def reserve(self) -> str | None:
        """Conta cada envio antes da chamada, inclusive se o provedor falhar."""
        with self._lock:
            now = monotonic()
            while self._attempts and self._attempts[0] <= now - DAY_SECONDS:
                self._attempts.popleft()
            if len(self._attempts) >= DAILY_LIMIT:
                return "A demo atingiu o limite diário. Volte mais tarde."
            if len(self._attempts) >= MINUTE_LIMIT and self._attempts[-MINUTE_LIMIT] > now - 60:
                return "A demo está recebendo várias mensagens. Tente novamente em instantes."
            self._attempts.append(now)
            return None
