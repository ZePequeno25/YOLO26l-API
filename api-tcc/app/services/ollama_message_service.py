import logging
import os
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
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                env=env,
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

            # Remove sequências de escape ANSI/VT100 que o Ollama imprime no terminal
            # (ex: \x1b[3D, \x1b[K, \x1b[?25l, etc.)
            import re as _re
            message = _re.sub(r"\x1b(\[[0-9;?]*[A-Za-z]|[()][AB012]|=|>|~)", "", message)
            
            # Remove linhas que contenham termos técnicos indesejados
            lines = []
            for line in message.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Filtro de palavras técnicas e formatos indesejados
                if any(keyword in line.lower() for keyword in [
                    "modelo", "contagem", "cadeiras", "frames", "class_counts",
                    "processado", "dados", "análise", "contexto", "vídeo", "imagem",
                    "objeto", "detectado", "resultado", "array", "json", "compute",
                    "shader", "gpu", "cuda", "tensor", "batch", "inference"
                ]):
                    continue
                # Remove linhas que parecem JSON ou código
                if line.startswith(('{', '[', '}', ']', '<', '```', '~~~', '###')):
                    continue
                # Remove markdown pesado
                if _re.search(r"[*_`]{2,}|^#|^>|^\|", line):
                    continue
                lines.append(line)
            
            message = " ".join(lines).strip()
            
            # Garante que começa com "Formalmente" ou similar padrão
            if message and not any(msg in message.lower() for msg in ["formalmente", "encontrou", "nenhum"]):
                # Se a resposta não segue o padrão, melhor usar o fallback
                logger.warning("Resposta do Ollama não segue padrão esperado. Usando fallback.")
                return self._build_fallback_message(analysis_result, analysis_model)
            
            if not message:
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

        classes_str = ", ".join(f"{k}: {v}" for k, v in class_counts.items()) if class_counts else "nenhum objeto"

        return (
            "Você é um assistente de análise simples.\n"
            "Responda com UMA frase MUITO CURTA em português, de forma formal e direta.\n"
            "PADRÃO: 'Formalmente encontrou X cadeira(s)'.\n"
            "NÃO inclua explicações, técnicas, modelos, frames ou dados técnicos.\n"
            "NÃO use markdown, caracteres especiais ou múltiplas frases.\n"
            "Responda APENAS com a mensagem simples, nada mais.\n\n"
            f"Objetos detectados: {classes_str}\n"
            f"Total de cadeiras: {detected_chairs}\n"
        )

    @staticmethod
    def _build_fallback_message(analysis_result: Dict[str, Any], analysis_model: str) -> str:
        class_counts = analysis_result.get("class_counts", {}) or {}
        detected_chairs = int(analysis_result.get("detected_chairs", 0) or 0)

        if not class_counts or detected_chairs == 0:
            return "Formalmente nenhum objeto foi detectado."

        chair_text = "cadeira" if detected_chairs == 1 else "cadeiras"
        return f"Formalmente encontrou {detected_chairs} {chair_text}."

    def generate_error_message(self, error_hint: str) -> str:
        """Passa um erro de validação ao Ollama para gerar mensagem amigável ao usuário.
        Nunca expõe informações do sistema. Se Ollama falhar, usa fallback genérico."""
        if not settings.ENABLE_PERSONALIZED_MESSAGE:
            return self._build_fallback_error_message(error_hint)

        prompt = (
            "Você é um assistente que informa o usuário sobre um problema com o arquivo enviado.\n"
            "Responda com UMA frase curta e amigável em português.\n"
            "NÃO mencione caminhos, servidores, código, técnicas ou dados internos.\n"
            "NÃO use markdown, aspas ou caracteres especiais.\n"
            "Contexto do problema: " + error_hint + "\n"
        )

        try:
            command = [self.command, "run", self.model]
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                env=env,
                check=False,
            )  # nosec B603

            if result.returncode != 0 or not (result.stdout or "").strip():
                return self._build_fallback_error_message(error_hint)

            import re as _re
            message = _re.sub(r"\x1b(\[[0-9;?]*[A-Za-z]|[()][AB012]|=|>|~)", "", result.stdout).strip()
            # Remove linhas com informações técnicas
            lines = [
                ln.strip() for ln in message.splitlines()
                if ln.strip() and not any(k in ln.lower() for k in [
                    "path", "sistema", "server", "api", "stack", "exception",
                    "erro interno", "traceback", "file", "diretório"
                ])
                and not ln.strip().startswith(('{', '[', '<', '```', '###'))
            ]
            message = " ".join(lines).strip()
            return message if message else self._build_fallback_error_message(error_hint)

        except Exception as exc:
            logger.warning("Ollama erro ao gerar mensagem de erro: %s", exc)
            return self._build_fallback_error_message(error_hint)

    @staticmethod
    def _build_fallback_error_message(error_hint: str) -> str:
        """Mensagens amigáveis sem expor detalhes do sistema."""
        hint = (error_hint or "").lower()
        if "longo" in hint or "duration" in hint or "segundo" in hint:
            return "O vídeo enviado é muito longo. Por favor, envie um clipe de no máximo 30 segundos."
        if "formato" in hint or "suportado" in hint:
            return "O formato do arquivo não é suportado. Envie uma imagem (JPG, PNG) ou vídeo (MP4)."
        if "vazio" in hint or "empty" in hint:
            return "O arquivo recebido está vazio. Tente novamente com um arquivo válido."
        if "grande" in hint or "size" in hint or "mb" in hint:
            return "O arquivo é muito grande. Reduza o tamanho e tente novamente."
        return "Não foi possível processar o arquivo enviado. Verifique o formato e tente novamente."
