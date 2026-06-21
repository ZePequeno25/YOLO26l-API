"""
Authentication routes module.
Handles token verification, Google Sign-in flow, and custom API token issuing.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, TypedDict, Union, cast

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request

from app.core import firebase as firebase_core
from app.core.firebase import (
    TokenValidationError,
    generate_api_token,
    generate_test_token,
    get_db,
    verify_id_token,
)
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.models.auth import (
    ApiTokenResponse,
    AuthResponse,
    GoogleAuthRequest,
    GoogleAuthResponse,
)
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Rate limiter específico para rotas de autenticação
_auth_limiter = SlidingWindowRateLimiter(
    max_hits=settings.AUTH_RATE_LIMIT_MAX,
    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW,
    block_seconds=settings.AUTH_RATE_LIMIT_BLOCK,
)


class ApiTokenData(TypedDict):
    """Type definition for custom API Token response structures."""
    access_token: str
    token_type: str
    expires_in: int


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None

    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        normalized = _normalize_token(parts[1])
        return normalized or None

    # Compatibilidade: alguns clientes enviam apenas o token cru no Authorization.
    normalized = _normalize_token(authorization)
    return normalized or None


def _normalize_token(token: Optional[str]) -> str:
    value = (token or "").strip().strip('"').strip("'")
    while value.lower().startswith("bearer "):
        value = value[7:].strip().strip('"').strip("'")
    return value


def _ensure_claims_dict(decoded: object) -> Dict[str, Any]:
    if not isinstance(decoded, dict):
        raise HTTPException(status_code=401, detail="Token invalido: payload inesperado")
    return cast(Dict[str, Any], decoded)


def _verify_app_check(app_check_token: str) -> Dict[str, Any]:
    """
    Verifica App Check token. Em desenvolvimento, permite placeholder tokens com aviso.
    Em produção, valida obrigatoriamente.
    """
    if not app_check_token or app_check_token.strip() == "":
        logger.warning("⚠️ App Check token ausente. Continue apenas em desenvolvimento.")
        return {}

    try:
        verifier = getattr(firebase_core, "verify_app_check_token")
        result = cast(Dict[str, Any], verifier(app_check_token))
        logger.info("✅ App Check token válido")
        return result
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Em desenvolvimento, placeholder tokens são esperados
        logger.warning("⚠️ App Check token inválido (esperado em dev): %s", str(e))
        return {}


async def _extract_request_token(
    request: Request,
    id_token: Optional[str] = None,
    authorization: Optional[str] = None,
) -> str:
    if id_token:
        normalized = _normalize_token(id_token)
        if normalized:
            return normalized

    bearer_token = _extract_bearer_token(authorization)
    if bearer_token:
        return bearer_token

    try:
        content_type = (request.headers.get("content-type") or "").lower()
        payload: Dict[str, Any] = {}

        if "application/json" in content_type:
            parsed = await request.json()
            if isinstance(parsed, dict):
                payload = cast(Dict[str, Any], parsed)
        else:
            form = await request.form()
            payload = dict(form.items())

        for key in ("id_token", "idToken", "access_token", "accessToken", "token"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                normalized = _normalize_token(value)
                if normalized:
                    return normalized
    except Exception:  # pylint: disable=broad-exception-caught
        logger.debug("Nao foi possivel extrair token do corpo da requisicao.", exc_info=True)

    raise HTTPException(status_code=401, detail="Token ausente ou em formato nao suportado.")


@router.post("/verify", response_model=AuthResponse)
async def verify_token(
    request: Request,
    id_token: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
):
    """
    Verifies the client-provided authentication token,
    upserting the user profile in Firestore.
    """
    try:
        token = await _extract_request_token(
            request, id_token=id_token, authorization=authorization
        )
        decoded = _ensure_claims_dict(cast(object, verify_id_token(token)))
        uid = str(decoded.get("uid") or "").strip()
        if not uid:
            raise HTTPException(status_code=401, detail="Token invalido: uid ausente")

        email = cast(Optional[str], decoded.get("email"))
        name = cast(Optional[str], decoded.get("name"))
        email_verified = bool(decoded.get("email_verified", True))
        now_iso = _utcnow_iso()

        database = get_db()
        user_ref = cast(Any, database.collection("users").document(uid))
        user_doc = user_ref.get()

        if not bool(getattr(user_doc, "exists", False)):
            user_ref.set({
                "email": email,
                "name": name,
                "created_at": now_iso,
                "last_login": now_iso,
            })

        return AuthResponse(
            uid=uid,
            email=email,
            name=name,
            email_verified=email_verified,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.get("/test-token")
async def get_test_token(
    uid: str = "admin-test-user",
    email: str = "admin@test.local",
    name: str = "Admin Teste"
):
    """
    Gera um JWT de teste válido para testes locais.
    ⚠️ Use apenas em ambiente de desenvolvimento!

    Exemplos:
    - GET /auth/test-token (gera token admin padrão)
    - GET /auth/test-token?uid=user123&email=user@test.local&name=User%20Test
    """
    try:
        if not settings.DEBUG:
            raise HTTPException(status_code=404, detail="Nao encontrado")

        token = generate_test_token(uid=uid, email=email, name=name)
        return {
            "token": token,
            "uid": uid,
            "email": email,
            "name": name,
            "expires_in": "24 hours"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/token", response_model=ApiTokenResponse)
async def issue_api_token(
    request: Request,
    id_token: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    x_firebase_appcheck: Optional[str] = Header(None),
    _rl: None = Depends(_auth_limiter),
):
    """
    Emite um JWT da própria API após validar o id_token (Firebase ou JWT local de teste).
    Use este endpoint no Android para obter access_token Bearer da API.
    """
    try:
        _verify_app_check(x_firebase_appcheck or "")
        token = await _extract_request_token(
            request, id_token=id_token, authorization=authorization
        )
        decoded = _ensure_claims_dict(cast(object, verify_id_token(token)))
        uid = str(decoded.get("uid") or "").strip()
        if not uid:
            raise HTTPException(status_code=401, detail="Token invalido: uid ausente")

        email = cast(Optional[str], decoded.get("email"))
        name = cast(Optional[str], decoded.get("name"))
        email_verified = bool(decoded.get("email_verified", True))
        admin = bool(decoded.get("admin", False))

        token_data = cast(
            ApiTokenData,
            generate_api_token(
                uid=uid,
                email=email,
                name=name,
                email_verified=email_verified,
                admin=admin,
            ),
        )

        return ApiTokenResponse(
            success=True,
            message="Token gerado com sucesso",
            uid=uid,
            email=email,
            name=name,
            email_verified=email_verified,
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


# pylint: disable=too-many-locals
@router.post("/google", response_model=GoogleAuthResponse)
async def authenticate_google(
    _request: Request,
    req: GoogleAuthRequest,
    x_firebase_appcheck: Optional[str] = Header(None),
    _rl: None = Depends(_auth_limiter),
):
    """
    Autentica usuário com Google.

    Recebe:
    - id_token: Token JWT do Google
    - email: Email do usuário
    - displayName: Nome de exibição do usuário

    Retorna:
    - Dados do usuário autenticado
    - Indicador se é novo usuário
    """
    try:
        _verify_app_check(x_firebase_appcheck or "")
        logger.info("🔐 Autenticação Google iniciada para: %s", req.email)

        # 1. Validar o id_token com Firebase
        decoded = _ensure_claims_dict(cast(object, verify_id_token(req.id_token)))
        uid = str(decoded.get("uid") or req.email).strip()  # Usar email como fallback para uid

        logger.info("✅ Token validado com sucesso. UID: %s", uid)

        # 2. Acessar Firestore
        database = get_db()
        user_ref = cast(Any, database.collection("users").document(uid))
        user_doc = user_ref.get()

        # 3. Verificar se é novo usuário
        is_new_user = not user_doc.exists

        # 4. Criar ou atualizar usuário
        if is_new_user:
            logger.info("👤 Novo usuário detectado: %s", req.email)
            now_iso = _utcnow_iso()
            user_ref.set({
                "uid": uid,
                "email": req.email,
                "name": req.displayName,
                "auth_provider": "google",
                "created_at": now_iso,
                "last_login": now_iso,
                "is_active": True
            })
        else:
            logger.info("🔄 Atualizando último login para: %s", req.email)
            user_ref.update({
                "last_login": _utcnow_iso(),
                "email": req.email,
                "name": req.displayName,
            })

        logger.info("✅ Autenticação concluída com sucesso para: %s", req.email)

        email_verified = bool(decoded.get("email_verified", True))
        admin = bool(decoded.get("admin", False))

        token_data = cast(
            ApiTokenData,
            generate_api_token(
                uid=uid,
                email=req.email,
                name=req.displayName,
                email_verified=email_verified,
                admin=admin,
            ),
        )

        # 5. Retornar resposta
        return GoogleAuthResponse(
            success=True,
            message=(
                "Autenticação concluída com sucesso"
                if not is_new_user
                else "Usuário criado com sucesso"
            ),
            uid=uid,
            email=req.email,
            name=req.displayName,
            email_verified=email_verified,
            is_new_user=is_new_user,
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
        )

    except HTTPException:
        raise
    except TokenValidationError as ve:
        logger.error("❌ App Check / token inválido: %s", ve)
        raise HTTPException(status_code=401, detail=str(ve)) from ve
    except ValueError as ve:
        error_msg = f"Erro de validação: {str(ve)}"
        logger.error("❌ %s", error_msg)
        raise HTTPException(status_code=400, detail=error_msg) from ve
    except Exception as e:
        error_msg = f"Erro na autenticação Google: {str(e)}"
        logger.error("❌ %s", error_msg, exc_info=True)
        raise HTTPException(status_code=401, detail=error_msg) from e