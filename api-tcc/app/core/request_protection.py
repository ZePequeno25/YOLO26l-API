import logging
import time
import ipaddress
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Dict, List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.firebase import TokenExpiredError, TokenValidationError, verify_id_token
from config.settings import settings

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None

    def _normalize(value: str | None) -> str:
        cleaned = (value or "").strip().strip('"').strip("'")
        while cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip().strip('"').strip("'")
        return cleaned

    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        normalized = _normalize(parts[1])
        return normalized or None

    normalized = _normalize(authorization)
    return normalized or None


class RequestProtectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._hits: Dict[str, List[float]] = defaultdict(list)
        self._blocked: Dict[str, float] = {}
        self._permanent_blacklist: set[str] = set()
        self._admin_honeypot_paths: set[str] = {
            p.strip().lower().rstrip("/") or "/"
            for p in settings.ADMIN_HONEYPOT_PATHS.split(",")
            if p.strip()
        }
        self._blacklist_file = Path(settings.PERMANENT_BLACKLIST_FILE)
        self._lock = Lock()
        self._public_paths = {
            "/auth/google",
            "/auth/token",
            "/auth/verify",
            "/errors/report",
            "/detection/models",
        }
        self._load_permanent_blacklist()
        if settings.DEBUG:
            self._public_paths.add("/auth/test-token")

    def _load_permanent_blacklist(self) -> None:
        try:
            if not self._blacklist_file.exists():
                return

            content = self._blacklist_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                ip = line.strip()
                if ip and not ip.startswith("#"):
                    self._permanent_blacklist.add(ip)

            if self._permanent_blacklist:
                logger.warning(
                    "Blacklist permanente carregada: %d IP(s)",
                    len(self._permanent_blacklist),
                )
        except Exception as err:
            logger.error("Falha ao carregar blacklist permanente: %s", err)

    def _persist_permanent_blacklist(self) -> None:
        try:
            self._blacklist_file.parent.mkdir(parents=True, exist_ok=True)
            lines = sorted(self._permanent_blacklist)
            self._blacklist_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        except Exception as err:
            logger.error("Falha ao persistir blacklist permanente: %s", err)

    def _add_to_permanent_blacklist(self, ip: str, reason: str) -> None:
        if ip in self._permanent_blacklist:
            return

        self._permanent_blacklist.add(ip)
        self._persist_permanent_blacklist()
        logger.critical("IP adicionado a blacklist permanente: ip=%s motivo=%s", ip, reason)

    def _blackhole_response(self) -> Response:
        return self._apply_security_headers(Response(status_code=404, content=b""))

    @staticmethod
    def _is_local_or_private_ip(ip: str) -> bool:
        try:
            parsed = ipaddress.ip_address(ip)
        except ValueError:
            return False

        return (
            parsed.is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_reserved
            or parsed.is_multicast
            or parsed.is_unspecified
        )

    def _enforce_no_local_requests(self, request: Request) -> Response | None:
        if not settings.BLOCK_LOCAL_REQUESTS:
            return None

        ip = _client_ip(request)
        if not self._is_local_or_private_ip(ip):
            return None

        logger.warning("Requisicao local/privada bloqueada: ip=%s path=%s", ip, request.url.path)
        return self._blackhole_response()

    def _enforce_admin_honeypot(self, request: Request) -> Response | None:
        if not settings.ENABLE_ADMIN_HONEYPOT:
            return None

        ip = _client_ip(request)
        normalized_path = request.url.path.strip().lower().rstrip("/") or "/"
        if normalized_path not in self._admin_honeypot_paths:
            return None

        with self._lock:
            self._add_to_permanent_blacklist(ip, reason=f"honeypot_path={request.url.path}")
            self._hits[ip] = []
            self._blocked.pop(ip, None)

        logger.critical("Honeypot acionado: ip=%s path=%s", ip, request.url.path)
        return self._blackhole_response()

    @staticmethod
    def _apply_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        return response

    @staticmethod
    def _is_system_route(path: str) -> bool:
        return (
            path.startswith("/system")
            or path.startswith("/errors")
            or path in {"/docs", "/redoc", "/openapi.json", "/detection/models", "/detection/analyze-test"}
            or path.startswith("/detection/metrics")
        )

    def _enforce_global_rate_limit(self, request: Request) -> Response | None:
        ip = _client_ip(request)
        now = time.monotonic()

        with self._lock:
            if ip in self._permanent_blacklist:
                logger.warning("IP em blacklist permanente tentou acesso: ip=%s path=%s", ip, request.url.path)
                return self._blackhole_response()

            release_at = self._blocked.get(ip)
            if release_at:
                if now < release_at:
                    remaining = int(release_at - now)
                    logger.warning("IP bloqueado por protecao global: ip=%s path=%s restam=%ds", ip, request.url.path, remaining)
                    return self._apply_security_headers(
                        JSONResponse(
                            status_code=429,
                            content={
                                "detail": "Muitas requisicoes. Aguarde antes de tentar novamente.",
                                "retry_after": remaining,
                            },
                            headers={"Retry-After": str(remaining)},
                        )
                    )

                del self._blocked[ip]
                self._hits[ip] = []

            cutoff = now - settings.GLOBAL_RATE_LIMIT_WINDOW
            self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]
            self._hits[ip].append(now)
            hit_count = len(self._hits[ip])

            if hit_count > settings.GLOBAL_RATE_LIMIT_MAX:
                if settings.GLOBAL_PERMANENT_BLACKLIST_ON_BURST:
                    self._add_to_permanent_blacklist(
                        ip,
                        reason=(
                            f"rajada_global hits={hit_count} "
                            f"janela={settings.GLOBAL_RATE_LIMIT_WINDOW}s"
                        ),
                    )
                    self._hits[ip] = []
                    self._blocked.pop(ip, None)
                    return self._blackhole_response()

                self._blocked[ip] = now + settings.GLOBAL_RATE_LIMIT_BLOCK
                self._hits[ip] = []
                logger.warning(
                    "IP bloqueado por rajada global: ip=%s path=%s hits=%d janela=%ds bloqueio=%ds",
                    ip,
                    request.url.path,
                    hit_count,
                    settings.GLOBAL_RATE_LIMIT_WINDOW,
                    settings.GLOBAL_RATE_LIMIT_BLOCK,
                )
                return self._apply_security_headers(
                    JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Muitas requisicoes. Aguarde antes de tentar novamente.",
                            "retry_after": settings.GLOBAL_RATE_LIMIT_BLOCK,
                        },
                        headers={"Retry-After": str(settings.GLOBAL_RATE_LIMIT_BLOCK)},
                    )
                )

        return None

    def _enforce_request_size(self, request: Request) -> JSONResponse | None:
        content_length = request.headers.get("Content-Length")
        if not content_length:
            return None

        try:
            size = int(content_length)
        except ValueError:
            return None

        if size > settings.MAX_REQUEST_BODY_BYTES:
            logger.warning("Requisicao recusada por tamanho excessivo: ip=%s path=%s bytes=%d", _client_ip(request), request.url.path, size)
            return self._apply_security_headers(
                JSONResponse(
                    status_code=413,
                    content={"detail": "Arquivo ou corpo da requisicao excede o limite permitido."},
                )
            )
        return None

    def _hide_system_routes_without_admin(self, request: Request) -> JSONResponse | None:
        path = request.url.path
        if path in self._public_paths or not self._is_system_route(path):
            return None

        token = _extract_bearer_token(request)
        if not token:
            logger.warning("Rota de sistema ocultada sem autenticacao: ip=%s path=%s", _client_ip(request), path)
            return self._apply_security_headers(JSONResponse(status_code=404, content={"detail": "Nao encontrado"}))

        try:
            decoded = verify_id_token(token)
        except (TokenValidationError, TokenExpiredError):
            logger.warning("Rota de sistema ocultada com token invalido: ip=%s path=%s", _client_ip(request), path)
            return self._apply_security_headers(JSONResponse(status_code=404, content={"detail": "Nao encontrado"}))

        if not decoded.get("admin", False):
            logger.warning("Rota de sistema ocultada para usuario nao administrador: uid=%s path=%s", decoded.get("uid"), path)
            return self._apply_security_headers(JSONResponse(status_code=404, content={"detail": "Nao encontrado"}))

        return None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        local_block = self._enforce_no_local_requests(request)
        if local_block:
            return local_block

        honeypot = self._enforce_admin_honeypot(request)
        if honeypot:
            return honeypot

        rate_limited = self._enforce_global_rate_limit(request)
        if rate_limited:
            return rate_limited

        oversized = self._enforce_request_size(request)
        if oversized:
            return oversized

        hidden = self._hide_system_routes_without_admin(request)
        if hidden:
            return hidden

        response = await call_next(request)
        return self._apply_security_headers(response)