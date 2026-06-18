"""
Firebase Authentication and Database Integration Module.
Handles token verification (Firebase, API JWT, and local test JWT)
and database access client instantiation.
"""
import datetime
import logging
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, auth, firestore
import jwt

try:
    from firebase_admin import app_check as firebase_app_check
    _APP_CHECK_AVAILABLE = True
except ImportError:
    _APP_CHECK_AVAILABLE = False

from config.settings import settings

logger = logging.getLogger(__name__)

firebase_path = Path(__file__).resolve().parent.parent.parent / "firebase-service-account.json"
cred = credentials.Certificate(str(firebase_path))
firebase_app = firebase_admin.initialize_app(cred)
db = firestore.client()


class TokenValidationError(Exception):
    """Erro de autenticação para token inválido."""


class TokenExpiredError(TokenValidationError):
    """Erro específico para token expirado."""


def get_db():
    """
    Returns the Firestore database client.
    """
    return db


def verify_app_check_token(app_check_token: str) -> dict:
    """
    Valida o token do Firebase App Check.
    Lança TokenValidationError se inválido ou se App Check não estiver habilitado.
    Retorna silenciosamente (sem erro) quando ENABLE_APP_CHECK=False nos settings.
    """
    if not settings.ENABLE_APP_CHECK:
        return {}  # App Check desabilitado — ignora

    if not _APP_CHECK_AVAILABLE:
        raise TokenValidationError("Módulo App Check não disponível no firebase-admin instalado.")

    if not app_check_token:
        raise TokenValidationError("X-Firebase-AppCheck ausente. App Check é obrigatório.")

    try:
        decoded = firebase_app_check.verify_token(app_check_token)
        return decoded
    except Exception as e:
        raise TokenValidationError(f"App Check inválido: {e}") from e


def _verify_api_jwt(id_token: str) -> dict | None:
    """
    Attempts to decode and verify the token as an API-issued JWT.
    """
    if not settings.API_JWT_SECRET:
        return None

    try:
        decoded = jwt.decode(id_token, settings.API_JWT_SECRET, algorithms=["HS256"])
        if decoded.get("iss") == "api-tcc":
            logger.debug("Token da API valido para uid=%s", decoded.get("uid"))
            return decoded
        logger.debug("Token eh JWT mas nao eh token da API; tentando outros metodos.")
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Token expirado. Faça login novamente.") from e
    except jwt.InvalidTokenError:
        logger.debug("Token não é JWT da API; tentando outros métodos.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.debug("Falha ao validar JWT da API: %s", str(e), exc_info=True)

    return None


def _verify_test_jwt(id_token: str) -> dict | None:
    """
    Attempts to decode and verify the token as a local development test JWT.
    """
    if not settings.TEST_JWT_SECRET:
        return None

    try:
        decoded = jwt.decode(id_token, settings.TEST_JWT_SECRET, algorithms=["HS256"])
        logger.debug("Token de teste válido para uid=%s", decoded.get("uid"))
        return decoded
    except jwt.InvalidTokenError:
        logger.debug("Token nao eh JWT local de teste; tentando validacao Firebase.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.debug("Falha ao validar JWT de teste local: %s", str(e), exc_info=True)

    return None


def verify_id_token(id_token: str):
    """
    Verifies the given ID token. Supports administrative bypass tokens,
    API-issued JWTs, local test JWTs, and Firebase ID tokens.
    """
    # Bypass administrativo apenas quando explicitamente habilitado por configuração.
    if (
        settings.ALLOW_TEST_ADMIN_BYPASS_TOKEN
        and settings.ADMIN_BYPASS_TOKEN
        and id_token == settings.ADMIN_BYPASS_TOKEN
    ):
        return {
            "uid": "admin-test-user",
            "email": "admin@test.local",
            "name": "Admin Teste",
            "email_verified": True,
            "admin": True
        }

    # Tentar validar como JWT da API (assinado com API_JWT_SECRET)
    api_decoded = _verify_api_jwt(id_token)
    if api_decoded is not None:
        return api_decoded

    # Tentar validar como JWT de teste
    test_decoded = _verify_test_jwt(id_token)
    if test_decoded is not None:
        return test_decoded

    # Depois tentar validar com Firebase
    try:
        return auth.verify_id_token(id_token)
    except auth.ExpiredIdTokenError as e:
        raise TokenExpiredError("Token expirado. Faça login novamente.") from e
    except (auth.InvalidIdTokenError, auth.RevokedIdTokenError) as e:
        raise TokenValidationError("Token inválido. Faça login novamente.") from e
    except Exception as e:
        logger.warning("Erro inesperado ao validar token: %s", e)
        raise TokenValidationError("Token inválido. Faça login novamente.") from e


def generate_test_token(
    uid: str = "admin-test-user",
    email: str = "admin@test.local",
    name: str = "Admin Teste"
):
    """Gera um JWT de teste válido para admin (use apenas em ambiente de desenvolvimento)"""
    if not settings.TEST_JWT_SECRET:
        raise RuntimeError(
            "TEST_JWT_SECRET nao configurado. "
            "Defina essa variavel para habilitar /auth/test-token."
        )

    payload = {
        "uid": uid,
        "email": email,
        "name": name,
        "email_verified": True,
        "admin": True,
        "iat": int(datetime.datetime.utcnow().timestamp()),
        "exp": int((datetime.datetime.utcnow() + datetime.timedelta(hours=24)).timestamp())
    }
    token = jwt.encode(payload, settings.TEST_JWT_SECRET, algorithm="HS256")
    return token


def generate_api_token(
    uid: str,
    email: str | None = None,
    name: str | None = None,
    email_verified: bool = True,
    admin: bool = False,
):
    """Gera JWT da própria API para uso do cliente após login válido."""
    if not settings.API_JWT_SECRET:
        raise RuntimeError(
            "API_JWT_SECRET nao configurado. "
            "Defina essa variavel para habilitar emissao de token da API."
        )

    now = datetime.datetime.utcnow()
    now_ts = int(now.timestamp())
    exp_ts = int((now + datetime.timedelta(hours=settings.API_JWT_EXPIRE_HOURS)).timestamp())
    payload = {
        "uid": uid,
        "email": email,
        "name": name,
        "email_verified": email_verified,
        "admin": bool(admin),
        "iat": now_ts,
        "exp": exp_ts,
        "iss": "api-tcc",
        "token_type": "access",
    }

    token = jwt.encode(payload, settings.API_JWT_SECRET, algorithm="HS256")
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": int(datetime.timedelta(hours=settings.API_JWT_EXPIRE_HOURS).total_seconds()),
    }