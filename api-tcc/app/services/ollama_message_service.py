import logging
import subprocess  # nosec B404
from typing import Any, Dict
import re

from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaMessageService:
    def __init__(self):
        self.command = self._validate_command(settings.OLLAMA_COMMAND)
        self.model = self._validate_model(settings.OLLAMA_MODEL)
        self.timeout_seconds = settings.OLLAMA_TIMEOUT_SECONDS

    def generate_personalized_message(self, analysis_result: Dict[str, Any], analysis_model: str) -> str:
        if not settings.ENABLE_PERSONALIZED_MESSAGE:
            return self._build_fallback_message(analysis_result, analysis_model)

        prompt = self._build_prompt(analysis_result, analysis_model)

        try:
            command = [self.command, "run", self.model]
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )  # nosec B603

            if result.returncode != 0:
                logger.warning(
                    "Falha ao executar Ollama local (code=%s): %s",
                    result.returncode,
                    (result.stderr or "").strip(),
                )
                return self._build_fallback_message(analysis_result, analysis_model)

            message = (result.stdout or "").strip()
            if not message:
                logger.warning("Resposta vazia do Ollama local. Usando fallback local.")
                return self._build_fallback_message(analysis_result, analysis_model)

            return message
        except subprocess.TimeoutExpired as exc:
            logger.warning("Timeout ao executar Ollama local: %s", exc)
            return self._build_fallback_message(analysis_result, analysis_model)
        except FileNotFoundError:
            logger.warning("Comando do Ollama nao encontrado (%s). Usando fallback local.", self.command)
            return self._build_fallback_message(analysis_result, analysis_model)
        except Exception as exc:
            logger.warning("Erro inesperado ao usar Ollama local: %s", exc)
            return self._build_fallback_message(analysis_result, analysis_model)

    @staticmethod
    def _validate_command(command: str) -> str:
        clean = (command or "").strip()
        if clean != "ollama":
            raise ValueError("OLLAMA_COMMAND invalido. Use apenas 'ollama'.")
        return clean

    @staticmethod
    def _validate_model(model: str) -> str:
        clean = (model or "").strip()
        if len(clean) > 120:
            raise ValueError("OLLAMA_MODEL invalido: muito longo")
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", clean):
            raise ValueError("OLLAMA_MODEL invalido")
        return clean

    def _build_prompt(self, analysis_result: Dict[str, Any], analysis_model: str) -> str:
        class_counts = analysis_result.get("class_counts", {})
        num_frames = analysis_result.get("num_frames_processed", 0)
        frames_with_detections = analysis_result.get("frames_with_detections", 0)
        detected_chairs = analysis_result.get("detected_chairs", 0)

        return (
            "Voce e um assistente amigavel de visao computacional. "
            "Gere uma mensagem personalizada em portugues brasileiro para o usuario final, "
            "com no maximo 2 frases, objetiva e clara. "
            "Inclua qual modelo foi usado na analise e um resumo do resultado. "
            "Evite markdown e nao invente dados.\n\n"
            f"Modelo usado na analise: {analysis_model}\n"
            f"Contagem por classe: {class_counts}\n"
            f"Cadeiras detectadas: {detected_chairs}\n"
            f"Frames processados: {num_frames}\n"
            f"Frames com deteccao: {frames_with_detections}\n"
        )

    @staticmethod
    def _build_fallback_message(analysis_result: Dict[str, Any], analysis_model: str) -> str:
        class_counts = analysis_result.get("class_counts", {}) or {}
        detected_chairs = int(analysis_result.get("detected_chairs", 0) or 0)
        num_frames = int(analysis_result.get("num_frames_processed", 0) or 0)

        if not class_counts:
            return (
                f"Analise concluida com o modelo '{analysis_model}'. "
                "Nao foram detectados objetos na imagem ou video enviado."
            )

        classes_resume = ", ".join(f"{name}: {count}" for name, count in class_counts.items())
        return (
            f"Analise concluida com o modelo '{analysis_model}'. "
            f"Resultado: {classes_resume} (cadeiras: {detected_chairs}, frames processados: {num_frames})."
        )
