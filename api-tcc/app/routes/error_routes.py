"""
Error logging routes module.
Receives errors and exceptions reported by mobile clients and writes them to local daily log files.
"""
import logging
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.models.error_report import ErrorReportRequest, ErrorReportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/errors", tags=["Relatório de Erros"])

# Diretório base absoluto onde os logs de erros serão armazenados
ERRORS_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "errors"


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
async def report_error(request: Request):
    """
    Recebe uma exceção capturada no app mobile e salva em um arquivo
    de log organizado por usuário e data. Suporta fallback em caso de JSON malformado.

    Estrutura gerada:
        logs/errors/{username}/{YYYY-MM-DD}.log
    """
    body_bytes = await request.body()
    
    # Se o corpo for GZIP bruto, descompacta manualmente aqui para evitar que payloads
    # comprimidos do mobile sem cabeçalho Content-Encoding adequado falhem no parser.
    if body_bytes.startswith(b"\x1f\x8b"):
        try:
            import gzip
            body_bytes = gzip.decompress(body_bytes)
            logger.info("✓ Payload de erro descompactado manualmente (GZIP).")
        except Exception as e:
            logger.error("Falha ao descompactar GZIP manual no endpoint de erro: %s", e)
    
    # Registro de depuração para entender o formato bruto do mobile
    headers_dict = dict(request.headers)
    first_bytes_hex = body_bytes[:50].hex()
    logger.info("=== DEBUG ERROR REPORT ===")
    logger.info("Headers: %s", headers_dict)
    logger.info("Bytes (Hex): %s", first_bytes_hex)
    logger.info("Length: %d bytes", len(body_bytes))
    
    body_str = body_bytes.decode("utf-8", errors="replace")
    
    # Tenta desserializar o JSON recebido
    import json
    try:
        data = json.loads(body_str)
        body = ErrorReportRequest(**data)
    except Exception as parse_err:
        # Se for JSON malformado (ex: unescaped control chars do Android), salva como fallback
        logger.warning("Payload de log de erro malformado: %s. Salvando no formato bruto.", parse_err)
        
        # Se parecer com dados gzip/binary que não foram descompactados por alguma razão
        extra_info = ""
        if body_bytes.startswith(b"\x1f\x8b"):
            extra_info = "\n[Nota: Detectado cabeçalho GZIP bruto no payload]"
            
        body = ErrorReportRequest(
            username="unknown",
            exception_type="MalformedJSONPayload",
            message=f"O payload do mobile continha caracteres especiais não escapados ou JSON inválido.{extra_info}",
            stack_trace=body_str
        )

    try:
        log_path = _get_log_path(body.username)
        entry = _format_entry(body)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

        # Retorna o caminho relativo à pasta de logs de erros
        relative_path = str(log_path.relative_to(ERRORS_LOG_DIR))
        logger.info("Erro mobile registrado para '%s' em %s", body.username, relative_path)

        return ErrorReportResponse(
            success=True,
            message="Erro registrado com sucesso",
            log_file=relative_path,
        )

    except Exception as e:
        logger.error("Falha ao registrar erro mobile: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail="Não foi possível registrar o erro."
        ) from e
