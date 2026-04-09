from fastapi import APIRouter, Form, HTTPException
from app.models.auth import AuthResponse, GoogleAuthRequest, GoogleAuthResponse
from app.core.firebase import verify_id_token, get_db, generate_test_token
import firebase_admin.firestore
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.post("/verify", response_model=AuthResponse)
async def verify_token(id_token: str = Form(...)):
    try:
        decoded = verify_id_token(id_token)
        db = get_db()
        user_ref = db.collection("users").document(decoded["uid"])
        
        if not user_ref.get().exists:
            user_ref.set({
                "email": decoded.get("email"),
                "name": decoded.get("name"),
                "created_at": firebase_admin.firestore.SERVER_TIMESTAMP,
                "last_login": firebase_admin.firestore.SERVER_TIMESTAMP
            })

        return AuthResponse(
            uid=decoded["uid"],
            email=decoded.get("email"),
            name=decoded.get("name"),
            email_verified=decoded.get("email_verified", True)
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/test-token")
async def get_test_token(uid: str = "admin-test-user", email: str = "admin@test.local", name: str = "Admin Teste"):
    """
    Gera um JWT de teste válido para testes locais.
    ⚠️ Use apenas em ambiente de desenvolvimento!
    
    Exemplos:
    - GET /auth/test-token (gera token admin padrão)
    - GET /auth/test-token?uid=user123&email=user@test.local&name=User%20Test
    """
    try:
        token = generate_test_token(uid=uid, email=email, name=name)
        return {
            "token": token,
            "uid": uid,
            "email": email,
            "name": name,
            "expires_in": "24 hours"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google", response_model=GoogleAuthResponse)
async def authenticate_google(request: GoogleAuthRequest):
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
        logger.info(f"🔐 Autenticação Google iniciada para: {request.email}")
        
        # 1. Validar o id_token com Firebase
        decoded = verify_id_token(request.id_token)
        uid = decoded.get("uid") or request.email  # Usar email como fallback para uid
        
        logger.info(f"✅ Token validado com sucesso. UID: {uid}")
        
        # 2. Acessar Firestore
        db = get_db()
        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()
        
        # 3. Verificar se é novo usuário
        is_new_user = not user_doc.exists
        
        # 4. Criar ou atualizar usuário
        if is_new_user:
            logger.info(f"👤 Novo usuário detectado: {request.email}")
            user_ref.set({
                "uid": uid,
                "email": request.email,
                "name": request.displayName,
                "auth_provider": "google",
                "created_at": firebase_admin.firestore.SERVER_TIMESTAMP,
                "last_login": firebase_admin.firestore.SERVER_TIMESTAMP,
                "is_active": True
            })
        else:
            logger.info(f"🔄 Atualizando último login para: {request.email}")
            user_ref.update({
                "last_login": firebase_admin.firestore.SERVER_TIMESTAMP,
                "email": request.email,  # Atualizar email em caso de mudança
                "name": request.displayName,  # Atualizar nome em caso de mudança
            })
        
        logger.info(f"✅ Autenticação concluída com sucesso para: {request.email}")
        
        # 5. Retornar resposta
        return GoogleAuthResponse(
            success=True,
            message="Autenticação concluída com sucesso" if not is_new_user else "Usuário criado com sucesso",
            uid=uid,
            email=request.email,
            name=request.displayName,
            email_verified=decoded.get("email_verified", True),
            is_new_user=is_new_user
        )
        
    except ValueError as ve:
        error_msg = f"Erro de validação: {str(ve)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
        
    except Exception as e:
        error_msg = f"Erro na autenticação Google: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        raise HTTPException(status_code=401, detail=error_msg)