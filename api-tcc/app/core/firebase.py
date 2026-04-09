import firebase_admin
from firebase_admin import credentials, auth, firestore
import jwt
import datetime
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

cred = credentials.Certificate("firebase-service-account.json")
firebase_app = firebase_admin.initialize_app(cred)
db = firestore.client()

class TokenValidationError(Exception):
    """Erro de autenticação para token inválido."""


class TokenExpiredError(TokenValidationError):
    """Erro específico para token expirado."""

def get_db():
    return db

def verify_id_token(id_token: str):
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

    # Tentar validar como JWT de teste primeiro
    try:
        if settings.TEST_JWT_SECRET:
            decoded = jwt.decode(id_token, settings.TEST_JWT_SECRET, algorithms=["HS256"])
            return decoded
    except jwt.InvalidTokenError:
        logger.debug("Token nao eh JWT local de teste; tentando validacao Firebase.")
    except Exception:
        logger.debug("Falha ao validar JWT de teste local.", exc_info=True)

    # Depois tentar validar com Firebase
    try:
        return auth.verify_id_token(id_token)
    except auth.ExpiredIdTokenError as e:
        raise TokenExpiredError("Token expirado. Faça login novamente.") from e
    except (auth.InvalidIdTokenError, auth.RevokedIdTokenError) as e:
        raise TokenValidationError("Token inválido. Faça login novamente.") from e
    except Exception as e:
        raise TokenValidationError(f"Falha ao validar token: {str(e)}") from e


def generate_test_token(uid: str = "admin-test-user", email: str = "admin@test.local", name: str = "Admin Teste"):
    """Gera um JWT de teste válido para admin (use apenas em ambiente de desenvolvimento)"""
    if not settings.TEST_JWT_SECRET:
        raise RuntimeError("TEST_JWT_SECRET nao configurado. Defina essa variavel para habilitar /auth/test-token.")

    payload = {
        "uid": uid,
        "email": email,
        "name": name,
        "email_verified": True,
        "admin": True,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    token = jwt.encode(payload, settings.TEST_JWT_SECRET, algorithm="HS256")
    return token