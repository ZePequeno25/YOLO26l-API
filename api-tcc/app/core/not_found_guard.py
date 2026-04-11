"""
Middleware que monitora respostas 404 por IP.

- Conta quantas 404s cada IP acumula em uma janela deslizante.
- Ao atingir o limite, bloqueia o IP pelo tempo configurado (retorna 403).
- Registra o evento no logger para auditoria.
"""

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

from fastapi import Request, Response
from starlette.types import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse

from config.settings import settings

logger = logging.getLogger(__name__)


class NotFoundGuard(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # {ip: [timestamp, ...]} — timestamps das 404s na janela
        self._hits: Dict[str, List[float]] = defaultdict(list)
        # {ip: tempo_de_liberação}
        self._blocked: Dict[str, float] = {}
        self._lock = Lock()

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        ip = self._client_ip(request)
        now = time.monotonic()

        # Verificar se o IP está bloqueado
        with self._lock:
            release_at = self._blocked.get(ip)
            if release_at:
                if now < release_at:
                    remaining = int(release_at - now)
                    logger.warning(
                        "IP BLOQUEADO tentou acessar: ip=%s path=%s restam=%ds",
                        ip, request.url.path, remaining,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Acesso temporariamente bloqueado por comportamento suspeito.",
                            "retry_after": remaining,
                        },
                        headers={"Retry-After": str(remaining)},
                    )
                else:
                    # Expirou o bloqueio — liberar
                    del self._blocked[ip]
                    self._hits[ip] = []

        response: Response = await call_next(request)

        if response.status_code == 404:
            window = settings.NOT_FOUND_WINDOW_SECONDS
            threshold = settings.NOT_FOUND_MAX_HITS
            block_duration = settings.NOT_FOUND_BLOCK_SECONDS

            with self._lock:
                cutoff = now - window
                # Manter apenas hits dentro da janela
                self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]
                self._hits[ip].append(now)

                hit_count = len(self._hits[ip])
                logger.debug(
                    "404 de ip=%s path=%s total_na_janela=%d janela=%ss limiar=%d",
                    ip,
                    request.url.path,
                    hit_count,
                    window,
                    threshold,
                )

                if hit_count >= threshold:
                    self._blocked[ip] = now + block_duration
                    self._hits[ip] = []
                    logger.warning(
                        "IP BLOQUEADO por rajada de 404: ip=%s hits=%d janela=%ss bloqueio=%ds",
                        ip,
                        hit_count,
                        window,
                        block_duration,
                    )

        return response
