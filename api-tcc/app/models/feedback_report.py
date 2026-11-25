"""
Pydantic schemas for User Feedback reports.
"""
# pylint: disable=too-few-public-methods
from pydantic import BaseModel, Field, field_validator


class FeedbackRequest(BaseModel):
    """Modelo para receber feedback do usuário via app mobile."""

    username: str = Field(..., description="Email ou display name do usuário")
    text: str = Field(..., description="Texto do feedback (máximo 1000 caracteres)")
    app_version: str | None = Field(None, description="Versão do app")
    device_info: str | None = Field(None, description="Informações do dispositivo")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validates that feedback text is not empty and fits size limits."""
        v = v.strip()
        if not v:
            raise ValueError("O feedback não pode estar vazio.")
        if len(v) > 1000:
            raise ValueError("O feedback não pode ter mais de 1000 caracteres.")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validates that username is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("O username não pode estar vazio.")
        return v

    class Config:
        """Pydantic model configuration and examples."""
        json_schema_extra = {
            "example": {
                "username": "joao.silva@gmail.com",
                "text": "O app está muito bom! Só senti que a detecção demorava um pouco.",
                "app_version": "1.0.3",
                "device_info": "Android 13 / Samsung Galaxy A54",
            }
        }


class FeedbackResponse(BaseModel):
    """Schema representing user feedback confirmation response."""
    success: bool = True
    message: str
    next_allowed_date: str | None = Field(
        None, description="Data mínima para o próximo feedback (YYYY-MM-DD)"
    )

