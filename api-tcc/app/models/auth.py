from pydantic import BaseModel, Field

class AuthResponse(BaseModel):
    uid: str
    email: str | None = None
    name: str | None = None
    email_verified: bool = True


class GoogleAuthRequest(BaseModel):
    """Modelo para requisição de autenticação do Google"""
    id_token: str = Field(..., description="Token ID do Google")
    email: str = Field(..., description="Email do usuário")
    displayName: str = Field(..., description="Nome de exibição do usuário")


class GoogleAuthResponse(BaseModel):
    """Modelo para resposta de autenticação do Google"""
    success: bool = True
    message: str = "Autenticação concluída com sucesso"
    uid: str
    email: str
    name: str
    email_verified: bool = True
    is_new_user: bool = False  # Indica se foi criado um novo usuário