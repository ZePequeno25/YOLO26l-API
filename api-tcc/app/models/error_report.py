"""
Pydantic schemas for Error reporting from clients.
"""
# pylint: disable=too-few-public-methods
from typing import Optional

from pydantic import BaseModel, Field


class ErrorReportRequest(BaseModel):
    """Modelo para receber exceções reportadas pelo app mobile"""
    username: Optional[str] = Field("unknown", description="Nome da conta do usuário (email ou display name)")
    exception_type: Optional[str] = Field(
        "UnknownException", description="Tipo/classe da exceção (ex: NullPointerException)"
    )
    message: Optional[str] = Field("No message provided", description="Mensagem da exceção")
    stack_trace: Optional[str] = Field(None, description="Stack trace completo")
    screen: Optional[str] = Field(None, description="Tela/Activity onde ocorreu o erro")
    app_version: Optional[str] = Field(None, description="Versão do app")
    device_info: Optional[str] = Field(None, description="Informações do dispositivo")
    model_used: Optional[str] = Field(
        None,
        description="Modelo de detecção em uso quando o erro ocorreu (ex: 'chair')"
    )

    class Config:
        """Pydantic model configuration and examples."""
        json_schema_extra = {
            "example": {
                "username": "joao.silva@gmail.com",
                "exception_type": "NullPointerException",
                "message": "Attempt to invoke virtual method on a null object reference",
                "stack_trace": (
                    "java.lang.NullPointerException\n"
                    "\tat com.example.MainActivity.onCreate(MainActivity.java:42)"
                ),
                "screen": "MainActivity",
                "app_version": "1.0.3",
                "device_info": "Android 13 / Samsung Galaxy A54",
                "model_used": "chair"
            }
        }


class ErrorReportResponse(BaseModel):
    """Schema representing the error logging confirmation response."""
    success: bool = True
    message: str = "Erro registrado com sucesso"
    log_file: str = Field(..., description="Caminho relativo do arquivo de log gerado")
