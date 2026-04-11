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
    access_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None


class ApiTokenResponse(BaseModel):
    success: bool = True
    message: str = "Token gerado com sucesso"
    uid: str
    email: str | None = None
    name: str | None = None
    email_verified: bool = True
    access_token: str
    token_type: str = "Bearer"
    expires_in: int