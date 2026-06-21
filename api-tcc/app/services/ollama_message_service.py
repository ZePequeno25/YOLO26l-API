"""
Ollama message generation service module.
Uses a local Ollama instance to generate friendly, natural language
summaries of detection results or validation errors, falling back to local templates.
"""
# pylint: disable=too-many-branches, too-many-statements
import logging
import os
import re
import subprocess  # nosec B404
from typing import Any, Dict, Set

from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaMessageService:
    """
    Service to generate custom user feedback/messages using local Ollama model.
    """
    _CLASS_ALIASES = {
        "cadeira": {"cadeira", "chair", "chairs", "kursi"},
        "chair": {"cadeira", "chair", "chairs", "kursi"},
        "extintor": {
            "extintor",
            "extintor_de_incndio",
            "fire_extinguisher",
            "fire extinguisher",
        },
        "extintor_de_incndio": {
            "extintor",
            "extintor_de_incndio",
            "fire_extinguisher",
            "fire extinguisher",
        },
        "garrafa": {
            "garrafa",
            "garrafa_de_vidro",
            "glass_bottle",
            "glass bottle",
            "bottle",
        },
        "garrafa_de_vidro": {
            "garrafa",
            "garrafa_de_vidro",
            "glass_bottle",
            "glass bottle",
            "bottle",
        },
        "lata_de_vidro_marrom_lata_de_vidro_limpo_garrafa_de_vidro": {
            "lata_de_vidro_marrom_lata_de_vidro_limpo_garrafa_de_vidro",
            "brown_glass_bottle",
            "clear_glass_bottle",
            "glass_bottle",
            "glass bottle",
            "garrafa_de_vidro",
            "garrafa",
        },
    }

    def __init__(self):
        self.command = self._validate_command(settings.OLLAMA_COMMAND)
        self.model = self._validate_model(settings.OLLAMA_MODEL)
        self.timeout_seconds = settings.OLLAMA_TIMEOUT_SECONDS

    def generate_personalized_message(
        self, analysis_result: Dict[str, Any], analysis_model: str
    ) -> str:  # pylint: disable=too-many-return-statements
        """
        Generates a friendly and contextual summary message based on the detection results.
        """
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
            message = re.sub(r"\x1b(\[[0-9;?]*[A-Za-z]|[()][AB012]|=|>|~)", "", message)

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
                if re.search(r"[*_`]{2,}|^#|^>|^\|", line):
                    continue
                lines.append(line)

            message = " ".join(lines).strip()

            # Garante que começa com "Formalmente" ou similar padrão
            if message and not any(
                msg in message.lower() for msg in ["formalmente", "encontrou", "nenhum"]
            ):
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
            logger.warning(
                "Comando do Ollama nao encontrado (%s). Usando fallback local.",
                self.command
            )
            return self._build_fallback_message(analysis_result, analysis_model)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Erro inesperado ao usar Ollama local: %s", exc)
            return self._build_fallback_message(analysis_result, analysis_model)

    @staticmethod
    def _validate_command(command: str) -> str:
        """Validates that OLLAMA_COMMAND settings config is simple and safe."""
        clean = (command or "").strip()
        if clean != "ollama":
            raise ValueError("OLLAMA_COMMAND invalido. Use apenas 'ollama'.")
        return clean

    @staticmethod
    def _validate_model(model: str) -> str:
        """Validates that OLLAMA_MODEL settings config is safe."""
        clean = (model or "").strip()
        if len(clean) > 120:
            raise ValueError("OLLAMA_MODEL invalido: muito longo")
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", clean):
            raise ValueError("OLLAMA_MODEL invalido")
        return clean

    def _build_prompt(self, analysis_result: Dict[str, Any], requested_model: str) -> str:
        """Constructs the prompt detailing detected counts and user request constraints."""
        class_counts = {
            name: count
            for name, count in (analysis_result.get("class_counts", {}) or {}).items()
            if count > 0
        }
        aliases_str = ", ".join(sorted(self._aliases_for(requested_model)))

        classes_str = (
            ", ".join(f"{k}: {v}" for k, v in class_counts.items())
            if class_counts
            else "nenhum objeto"
        )

        return (
            "Você é um assistente de análise de imagem rigoroso.\n"
            "Responda com UMA frase MUITO CURTA em português, de forma formal e direta.\n"
            "PADRÃO: 'O usuário solicitou X, e foi encontrado Y'.\n"
            "A API executa todos os modelos disponiveis; use os objetos realmente encontrados "
            "para descrever a cena quando o solicitado nao aparecer.\n"
            "Considere aliases equivalentes do objeto solicitado como o mesmo objeto.\n"
            "Se encontrou o que foi pedido, diga: 'Formalmente encontrou ...'. "
            "Se não encontrou o pedido, diga: 'Não encontrou X, mas encontrou Y'.\n"
            "REGRA CRÍTICA: NÃO INVENTE OBJETOS. Se os 'Objetos realmente encontrados' "
            "for 'nenhum objeto', você DEVE responder EXATAMENTE: 'Não encontrou o objeto "
            "solicitado e não detectou nenhum outro objeto.'\n"
            "NÃO inclua explicações, técnicas, modelos, frames ou dados técnicos.\n"
            "NÃO use markdown, caracteres especiais ou múltiplas frases.\n"
            "Responda APENAS com a mensagem simples, nada mais.\n\n"
            f"Objeto solicitado pelo usuário: {requested_model}\n"
            f"Aliases equivalentes do solicitado: {aliases_str}\n"
            f"Objetos realmente encontrados na cena: {classes_str}\n"
        )

    @classmethod
    def _normalize_label(cls, label: str) -> str:
        """Helper to lower and underscore-strip category labels."""
        return (label or "").strip().lower().replace("-", "_").replace(" ", "_")

    @classmethod
    def _aliases_for(cls, label: str) -> Set[str]:
        """Looks up class name aliases from mappings."""
        normalized = cls._normalize_label(label)
        aliases = cls._CLASS_ALIASES.get(normalized, {normalized})
        return {cls._normalize_label(item) for item in aliases}

    @staticmethod
    def _format_found(class_counts: Dict[str, int]) -> str:
        """Formats category counts to string representations."""
        return ", ".join(f"{count} {name}" for name, count in class_counts.items())

    @classmethod
    def _build_fallback_message(
        cls, analysis_result: Dict[str, Any], requested_model: str
    ) -> str:
        """Template-based fallback message builder when Ollama is unavailable."""
        class_counts = {
            name: count
            for name, count in (analysis_result.get("class_counts", {}) or {}).items()
            if count > 0
        }

        if not class_counts:
            return f"Nenhum objeto foi detectado na cena (procurava-se {requested_model})."

        encontrados = cls._format_found(class_counts)
        requested_aliases = cls._aliases_for(requested_model)
        found_aliases = {
            alias
            for class_name in class_counts
            for alias in cls._aliases_for(class_name)
        }

        if requested_aliases & found_aliases:
            return f"Formalmente encontrou o que procurava: {encontrados}."
        return f"Nao encontrou {requested_model}, mas detectou na cena: {encontrados}."

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

            message = re.sub(
                r"\x1b(\[[0-9;?]*[A-Za-z]|[()][AB012]|=|>|~)", "", result.stdout
            ).strip()
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

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Ollama erro ao gerar mensagem de erro: %s", exc)
            return self._build_fallback_error_message(error_hint)

    @staticmethod
    def _build_fallback_error_message(error_hint: str) -> str:
        """Mensagens amigáveis sem expor detalhes do sistema."""
        hint = (error_hint or "").lower()
        if "longo" in hint or "duration" in hint or "segundo" in hint:
            return (
                "O vídeo enviado é muito longo. "
                "Por favor, envie um clipe de no máximo 30 segundos."
            )
        if "formato" in hint or "suportado" in hint:
            return (
                "O formato do arquivo não é suportado. "
                "Envie uma imagem (JPG, PNG) ou vídeo (MP4)."
            )
        if "vazio" in hint or "empty" in hint:
            return "O arquivo recebido está vazio. Tente novamente com um arquivo válido."
        if "grande" in hint or "size" in hint or "mb" in hint:
            return "O arquivo é muito grande. Reduza o tamanho e tente novamente."
        return (
            "Não foi possível processar o arquivo enviado. "
            "Verifique o formato e tente novamente."
        )
