import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.feedback_report import FeedbackRequest, FeedbackResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])

FEEDBACK_LOG_DIR = Path("logs/feedback")
COOLDOWN_DAYS = 5
MAX_ENTRIES_PER_DAY = 3  # segurança: evita flood mesmo dentro do cooldown


def _sanitize_username(username: str) -> str:
    """Remove caracteres inválidos para uso como nome de pasta."""
    sanitized = re.sub(r"[^\w\.\-@]", "_", username)
    return sanitized[:80]


def _user_dir(username: str) -> Path:
    safe = _sanitize_username(username)
    user_dir = FEEDBACK_LOG_DIR / safe
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _last_submission_date(user_dir: Path) -> date | None:
    """
    Retorna a data da submissão mais recente encontrada nos arquivos de log
    do usuário, ou None se ainda não há nenhuma.
    """
    log_files = sorted(user_dir.glob("????-??-??.log"), reverse=True)
    for f in log_files:
        try:
            return date.fromisoformat(f.stem)
        except ValueError:
            continue
    return None


def _count_entries_today(log_path: Path) -> int:
    """Conta quantas entradas já foram registradas no arquivo do dia."""
    if not log_path.exists():
        return 0
    with open(log_path, encoding="utf-8") as f:
        return f.read().count("TIMESTAMP")


def _format_entry(req: FeedbackRequest) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=" * 60,
        f"TIMESTAMP   : {now}",
        f"USUARIO     : {req.username}",
        f"FEEDBACK    : {req.text}",
    ]
    if req.app_version:
        lines.append(f"VERSAO APP  : {req.app_version}")
    if req.device_info:
        lines.append(f"DISPOSITIVO : {req.device_info}")
    lines.append("=" * 60 + "\n")
    return "\n".join(lines)


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(body: FeedbackRequest):
    """
    Recebe um feedback do usuário e salva em arquivo de log.

    Regras:
    - O primeiro feedback é sempre aceito.
    - Feedbacks subsequentes exigem intervalo mínimo de 5 dias desde o último.
    - Limite de 1000 caracteres (validado no modelo).

    Estrutura gerada:
        logs/feedback/{username}/{YYYY-MM-DD}.log
    """
    try:
        user_dir = _user_dir(body.username)
        last_date = _last_submission_date(user_dir)
        today = date.today()

        if last_date is not None:
            next_allowed = last_date + timedelta(days=COOLDOWN_DAYS)
            if today < next_allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "cooldown",
                        "message": (
                            f"Você já enviou um feedback recentemente. "
                            f"O próximo poderá ser enviado a partir de {next_allowed.isoformat()}."
                        ),
                        "next_allowed_date": next_allowed.isoformat(),
                    },
                )

        log_path = user_dir / f"{today.isoformat()}.log"

        if _count_entries_today(log_path) >= MAX_ENTRIES_PER_DAY:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "limit_reached",
                    "message": "Limite de feedbacks do dia atingido. Tente novamente amanhã.",
                    "next_allowed_date": (today + timedelta(days=1)).isoformat(),
                },
            )

        entry = _format_entry(body)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

        next_allowed_date = (today + timedelta(days=COOLDOWN_DAYS)).isoformat()
        logger.info(f"Feedback registrado para '{body.username}' em {log_path}")

        return FeedbackResponse(
            success=True,
            message="Feedback enviado com sucesso! Obrigado pela sua opinião.",
            next_allowed_date=next_allowed_date,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Falha ao registrar feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Não foi possível registrar o feedback.")
