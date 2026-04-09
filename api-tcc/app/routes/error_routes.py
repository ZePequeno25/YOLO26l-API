import logging
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.error_report import ErrorReportRequest, ErrorReportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/errors", tags=["Relatório de Erros"])

# Diretório base onde os logs de erros serão armazenados
ERRORS_LOG_DIR = Path("logs/errors")


def _sanitize_username(username: str) -> str:
    """Remove caracteres inválidos para uso como nome de pasta."""
    sanitized = re.sub(r"[^\w\.\-@]", "_", username)
    return sanitized[:80]  # limita tamanho para segurança


def _get_log_path(username: str) -> Path:
    """Retorna o Path do arquivo de log do dia para o usuário."""
    safe_name = _sanitize_username(username)
    date_str = datetime.now().strftime("%Y-%m-%d")
    user_dir = ERRORS_LOG_DIR / safe_name
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / f"{date_str}.log"


def _format_entry(report: ErrorReportRequest) -> str:
    """Formata uma entrada de log com timestamp e todos os campos recebidos."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"{'=' * 60}",
        f"TIMESTAMP   : {now}",
        f"USUARIO     : {report.username}",
        f"EXCEPTION   : {report.exception_type}",
        f"MENSAGEM    : {report.message}",
    ]
    if report.model_used:
        lines.append(f"MODELO      : {report.model_used}")
    if report.screen:
        lines.append(f"TELA        : {report.screen}")
    if report.app_version:
        lines.append(f"VERSAO APP  : {report.app_version}")
    if report.device_info:
        lines.append(f"DISPOSITIVO : {report.device_info}")
    if report.stack_trace:
        lines.append("STACK TRACE :")
        lines.append(report.stack_trace)
    lines.append(f"{'=' * 60}\n")
    return "\n".join(lines)


@router.post("/report", response_model=ErrorReportResponse, status_code=201)
async def report_error(body: ErrorReportRequest):
    """
    Recebe uma exceção capturada no app mobile e salva em um arquivo
    de log organizado por usuário e data.

    Estrutura gerada:
        logs/errors/{username}/{YYYY-MM-DD}.log
    """
    try:
        log_path = _get_log_path(body.username)
        entry = _format_entry(body)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

        relative_path = str(log_path)
        logger.info(f"Erro mobile registrado para '{body.username}' em {relative_path}")

        return ErrorReportResponse(
            success=True,
            message="Erro registrado com sucesso",
            log_file=relative_path,
        )

    except Exception as e:
        logger.error(f"Falha ao registrar erro mobile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Não foi possível registrar o erro.")
