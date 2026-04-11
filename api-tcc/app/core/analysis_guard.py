import time
from threading import Lock

from fastapi import HTTPException


class SingleAnalysisGuard:
    def __init__(self):
        self._active_users: set[str] = set()
        self._lock = Lock()

    def acquire(self, uid: str) -> None:
        with self._lock:
            if uid in self._active_users:
                raise HTTPException(
                    status_code=429,
                    detail="O usuario ja possui uma analise em andamento. Aguarde a conclusao antes de enviar outra.",
                )
            self._active_users.add(uid)

    def release(self, uid: str) -> None:
        with self._lock:
            self._active_users.discard(uid)


analysis_guard = SingleAnalysisGuard()