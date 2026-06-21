"""
Pydantic schemas for Authentication endpoints.
"""
# pylint: disable=too-few-public-methods
from typing import Optional

from pydantic import BaseModel, Field


class AuthResponse(BaseModel):
    """Schema representing authenticated user information."""
    uid: str
    email: Optional[str] = None
    name: Optional[str] = None
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
    access_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None


class ApiTokenResponse(BaseModel):
    """Schema representing the API token generation response."""
    success: bool = True
    message: str = "Token gerado com sucesso"
    uid: str
    email: Optional[str] = None
    name: Optional[str] = None
    email_verified: bool = True
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
