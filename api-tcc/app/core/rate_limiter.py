"""
Rate limiter de janela deslizante reutilizável como FastAPI Dependency.

Uso:
    limiter = SlidingWindowRateLimiter(max_hits=5, window_seconds=60, block_seconds=300)

    @router.post("/meu-endpoint")
    async def meu_endpoint(request: Request, _=Depends(limiter)):
        ...
"""

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class SlidingWindowRateLimiter:
    def __init__(self, max_hits: int, window_seconds: int, block_seconds: int = 300):
        self.max_hits = max_hits
        self.window = window_seconds
        self.block_seconds = block_seconds
        self._hits: Dict[str, List[float]] = defaultdict(list)
        self._blocked: Dict[str, float] = {}
        self._lock = Lock()

    def __call__(self, request: Request) -> None:
        ip = _client_ip(request)
        now = time.monotonic()

        with self._lock:
            # Verificar se está bloqueado
            release_at = self._blocked.get(ip)
            if release_at:
                if now < release_at:
                    remaining = int(release_at - now)
                    logger.warning(
                        "Rate limit bloqueado: ip=%s path=%s restam=%ds",
                        ip, request.url.path, remaining,
                    )
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "message": "Muitas tentativas. Aguarde antes de tentar novamente.",
                            "retry_after": remaining,
                        },
                        headers={"Retry-After": str(remaining)},
                    )
                else:
                    del self._blocked[ip]
                    self._hits[ip] = []

            # Registrar hit e verificar janela
            cutoff = now - self.window
            self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]
            self._hits[ip].append(now)
            count = len(self._hits[ip])

            logger.debug("Rate limit: ip=%s path=%s hits=%d/%d", ip, request.url.path, count, self.max_hits)

            if count > self.max_hits:
                del self._hits[ip]
                self._blocked[ip] = now + self.block_seconds
                remaining = self.block_seconds
                logger.warning(
                    "Rate limit atingido: ip=%s path=%s hits=%d bloqueio=%ds",
                    ip, request.url.path, count, self.block_seconds,
                )
                raise HTTPException(
                    status_code=429,
                    detail={
                        "message": "Muitas tentativas. Aguarde antes de tentar novamente.",
                        "retry_after": remaining,
                    },
                    headers={"Retry-After": str(remaining)},
                )
