from pydantic import BaseModel, Field
from typing import Optional


class ErrorReportRequest(BaseModel):
    """Modelo para receber exceções reportadas pelo app mobile"""
    username: str = Field(..., description="Nome da conta do usuário (email ou display name)")
    exception_type: str = Field(..., description="Tipo/classe da exceção (ex: NullPointerException)")
    message: str = Field(..., description="Mensagem da exceção")
    stack_trace: Optional[str] = Field(None, description="Stack trace completo")
    screen: Optional[str] = Field(None, description="Tela/Activity onde ocorreu o erro")
    app_version: Optional[str] = Field(None, description="Versão do app")
    device_info: Optional[str] = Field(None, description="Informações do dispositivo")
    model_used: Optional[str] = Field(None, description="Modelo de detecção em uso quando o erro ocorreu (ex: 'chair')")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "joao.silva@gmail.com",
                "exception_type": "NullPointerException",
                "message": "Attempt to invoke virtual method on a null object reference",
                "stack_trace": "java.lang.NullPointerException\n\tat com.example.MainActivity.onCreate(MainActivity.java:42)",
                "screen": "MainActivity",
                "app_version": "1.0.3",
                "device_info": "Android 13 / Samsung Galaxy A54",
                "model_used": "chair"
            }
        }


class ErrorReportResponse(BaseModel):
    success: bool = True
    message: str = "Erro registrado com sucesso"
    log_file: str = Field(..., description="Caminho relativo do arquivo de log gerado")
