"""
Module to guard against concurrent analyses for the same user.
"""
from threading import Lock

from fastapi import HTTPException


class SingleAnalysisGuard:
    """
    Guard class to ensure a single analysis runs per user at any given time.
    """
    def __init__(self):
        self._active_users: set[str] = set()
        self._lock = Lock()

    def acquire(self, uid: str) -> None:
        """
        Acquire a lock for the user's analysis.
        Raises HTTPException 429 if the user has an analysis in progress.
        """
        with self._lock:
            if uid in self._active_users:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "O usuario ja possui uma analise em andamento. "
                        "Aguarde a conclusao antes de enviar outra."
                    ),
                )
            self._active_users.add(uid)

    def release(self, uid: str) -> None:
        """
        Release the user's lock once the analysis is completed or failed.
        """
        with self._lock:
            self._active_users.discard(uid)


analysis_guard = SingleAnalysisGuard()