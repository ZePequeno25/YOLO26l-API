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
from typing import Any, Dict, Optional, Set

from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaMessageService:
    """
    Service to generate custom user feedback/messages using local Ollama model.
    """
    _CLASS_ALIASES = {
        "cadeira": {"cadeira", "chair", "chairs"},
        "chair": {"cadeira", "chair", "chairs"},
        "extintor": {
            "extintor",
            "extintor_de_incendio",
            "extintor de incêndio",
            "extintor_de_incêndio",
            "fire_extinguisher",
            "fire extinguisher",
            "babcock_davis_co2_portable",
            "walker_fire_mc_2a_co2",
            "walker_fire_mf_60_foam",
            "yamato_ya_10nx"
        },
        "extintor_de_incendio": {
            "extintor",
            "extintor_de_incendio",
            "extintor de incêndio",
            "extintor_de_incêndio",
            "fire_extinguisher",
            "fire extinguisher",
        },
        "pessoa": {"pessoa", "person", "people"},
        "person": {"pessoa", "person", "people"},
        "caminhao": {"caminhao", "caminhão", "truck"},
        "caminhão": {"caminhao", "caminhão", "truck"},
        "truck": {"caminhao", "caminhão", "truck"},
        "carro": {"carro", "car"},
        "car": {"carro", "car"},
        "luvas": {"luvas", "gloves", "sem luvas", "no-gloves", "no_gloves"},
        "gloves": {"luvas", "gloves", "sem luvas", "no-gloves", "no_gloves"},
        "capacete": {"capacete", "capacete de segurança", "hardhat", "sem capacete de segurança", "no-hardhat", "no_hardhat"},
        "hardhat": {"capacete", "capacete de segurança", "hardhat", "sem capacete de segurança", "no-hardhat", "no_hardhat"},
        "oculos": {"oculos de protecao", "óculos de proteção", "goggles", "sem oculos de protecao", "no-goggles", "no_goggles"},
        "goggles": {"oculos de protecao", "óculos de proteção", "goggles", "sem oculos de protecao", "no-goggles", "no_goggles"},
        "colete": {"colete de seguranca", "colete de segurança", "safety vest", "safety_vest", "sem colete de segurança", "no-safety vest", "no_safety_vest"},
        "safety_vest": {"colete de seguranca", "colete de segurança", "safety vest", "safety_vest", "sem colete de segurança", "no-safety vest", "no_safety_vest"},
        "mascara": {"mascara", "máscara", "mask", "sem máscara", "no-mask", "no_mask"},
        "mask": {"mascara", "máscara", "mask", "sem máscara", "no-mask", "no_mask"},
        "garrafa": {
            "garrafa",
            "garrafa_de_vidro",
            "glass_bottle",
            "glass bottle",
            "bottle",
            "brown_glass_bottle",
            "clear_glass_bottle"
        },
    }

    def __init__(self):
        self.command = self._validate_command(settings.OLLAMA_COMMAND)
        self.model = self._validate_model(settings.OLLAMA_MODEL)
        self.timeout_seconds = settings.OLLAMA_TIMEOUT_SECONDS

    def is_available(self) -> bool:
        """Verifica se o serviço local do Ollama está online e respondendo."""
        if not settings.ENABLE_PERSONALIZED_MESSAGE:
            return True
        
        # 1. Tenta pingar a porta HTTP local do Ollama
        import urllib.request
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                # Ollama normalmente retorna 200 "Ollama is running"
                if resp.status in (200, 404):
                    return True
        except Exception:
            pass

        # 2. Fallback: Tenta executar o comando cli do Ollama
        try:
            import subprocess
            result = subprocess.run(
                [self.command, "--version"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def _clean_duplicate_prefixes(text: str) -> str:
        """Resolve duplicidades comuns geradas por problemas de codificação ou repetições do Ollama."""
        cleaned = text
        for _ in range(2):
            # Corrige duplicidade de prefixos como "máscar máscara" ou "Seguran Segurança" ou "Nã Não"
            cleaned = re.sub(r'\b(\w{2,15})\s+\1(\w+)\b', r'\1\2', cleaned, flags=re.IGNORECASE)
            # Remove palavras inteiras duplicadas em sequência (ex: "o o", "que que")
            cleaned = re.sub(r'\b(\w+)\s+\1\b', r'\1', cleaned, flags=re.IGNORECASE)
        return cleaned

    def _call_ollama_http(self, prompt: str) -> Optional[str]:
        """Tenta fazer a chamada ao Ollama via API HTTP local com timeout curto de tempo real (2.0s)."""
        import json
        import urllib.request
        url = "http://127.0.0.1:11434/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "repeat_penalty": 1.3
            }
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            # Timeout curto de 2.0s para não congelar o fluxo da câmera do celular
            with urllib.request.urlopen(req, timeout=2.0) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                message = resp_data.get("response", "").strip()
                if message:
                    return message
        except Exception as exc:
            logger.debug("Ollama HTTP indisponível ou timeout: %s", exc)
        return None

    def _call_ollama(self, prompt: str) -> str:
        """Interface unificada que tenta primeiro HTTP e depois Subprocess."""
        # 1. Tenta API HTTP com timeout de 2s
        msg = self._call_ollama_http(prompt)
        if msg:
            return msg
        return ""

    @classmethod
    def _build_fallback_message(
        cls, analysis_result: Dict[str, Any], requested_model: str
    ) -> str:
        """Template enriquecido instantâneo (0.001s) quando Ollama está offline ou demorado."""
        class_counts = {
            name: count
            for name, count in (analysis_result.get("class_counts", {}) or {}).items()
            if count > 0
        }

        if not class_counts:
            return "Nenhum objeto relevante foi detectado na cena analisada."

        encontrados = cls._format_found(class_counts)
        compliance_status = analysis_result.get("compliance_status") or "CONFORME"
        status_text = "Conforme" if compliance_status == "CONFORME" else "Não Conforme (Alerta de Segurança)"

        # Extrair detalhes dos 5 componentes da sobcamada
        sub_layers = analysis_result.get("sub_layer_analysis") or []
        sub_desc = ""
        if sub_layers:
            parts = []
            for sl in sub_layers:
                passed = sl.get("passed_items", [])
                failed = sl.get("failed_items", [])
                if passed:
                    parts.append(f"Componentes Conformes: {', '.join(passed)}")
                if failed:
                    parts.append(f"Irregularidades: {', '.join(failed)}")
            if parts:
                sub_desc = f". {'; '.join(parts)}"

        return f"A análise identificou {encontrados}{sub_desc}. Status: {status_text}."

    def generate_personalized_message(
        self, analysis_result: Dict[str, Any], analysis_model: str
    ) -> str:
        """
        Generates a friendly and contextual summary message based on the detection results.
        """
        if not settings.ENABLE_PERSONALIZED_MESSAGE:
            return self._build_fallback_message(analysis_result, analysis_model)

        prompt = self._build_prompt(analysis_result, analysis_model)
        message = self._call_ollama(prompt)

        if not message:
            return self._build_fallback_message(analysis_result, analysis_model)

        # Remove sequências de escape ANSI/VT100
        message = re.sub(r"\x1b(\[[0-9;?]*[A-Za-z]|[()][AB012]|=|>|~)", "", message)

        # Filtro de linhas com informações técnicas
        lines = []
        for line in message.splitlines():
            line = line.strip()
            if not line:
                continue
            if any(keyword in line.lower() for keyword in [
                "class_counts", "processado", "dados", "resultado", "array", "json",
                "compute", "shader", "gpu", "cuda", "tensor", "batch", "inference"
            ]):
                continue
            if line.startswith(('{', '[', '}', ']', '<', '```', '~~~', '###')):
                continue
            if re.search(r"[*_`]{2,}|^#|^>|^\|", line):
                continue
            lines.append(line)

        message = " ".join(lines).strip()

        if not message:
            return self._build_fallback_message(analysis_result, analysis_model)

        # Remove qualquer sufixo repetido gerado pelo Ollama que imita o formato de prompt
        # (ex: "Status: NÃO CONFORME", "Alertas de Segurança: ...")
        message = re.split(r'(?i)\b(?:status|alertas|conformidade)\b', message)[0].strip()
        # Remove resíduos de pontuação que sobram no corte da divisão
        message = re.sub(r'[:;\s,-]+$', '', message).strip()
        if message and not message.endswith('.'):
            message += '.'

        # Limpar duplicidades de codificação no português antes de retornar
        return self._clean_duplicate_prefixes(message)

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
        """Constructs the prompt detailing detected counts, sub-layers, and constraints."""
        class_counts = {
            name: count
            for name, count in (analysis_result.get("class_counts", {}) or {}).items()
            if count > 0
        }

        classes_str = (
            ", ".join(f"{v} {k}" for k, v in class_counts.items())
            if class_counts
            else "nenhum objeto relevante"
        )

        compliance_status = analysis_result.get("compliance_status") or "CONFORME"
        alerts = analysis_result.get("compliance_alerts") or []
        alerts_str = "; ".join(alerts) if alerts else "Nenhuma inconformidade de segurança detectada."

        # Extrair análise em sobcamada (os 5 componentes: Trava, Mangueira, Adesivo, Gás/Pressão, Sinalização)
        sub_layers = analysis_result.get("sub_layer_analysis") or []
        sub_details_str = ""
        if sub_layers:
            sub_summary = []
            for sl in sub_layers:
                obj_cls = sl.get("object_class", "Objeto")
                passed = ", ".join(sl.get("passed_items", [])) or "Nenhum"
                failed = ", ".join(sl.get("failed_items", [])) or "Nenhum"
                sub_summary.append(f"  • Objeto: {obj_cls} | Aprovados: [{passed}] | Faltando/Irregulares: [{failed}]")
            sub_details_str = "\nDetalhamento da Sobcamada (Componentes Específicos):\n" + "\n".join(sub_summary) + "\n"

        return (
            "Você é um engenheiro auditor de segurança do trabalho e conformidade física em tempo real.\n"
            "Gere um laudo/resumo formal, técnico e direto da análise da cena em uma única frase em português.\n"
            "NÃO use primeira pessoa e evite termos informais.\n"
            "Quando um Extintor de Incêndio for analisado, reporte explicitamente o estado dos componentes: Trava de Segurança, Mangueira/Difusor, Adesivo/Rotulagem, Carga de Gás/Pressão e Sinalização de Emergência de Parede.\n"
            "Exemplo:\n"
            "- 'A análise da cena identificou 1 Extintor de Incêndio. Componentes conformes: Trava e Sinalização; Irregularidades: Mangueira desconectada e Carga de Gás/Pressão baixa. Status: Não Conforme.'\n\n"
            f"Objetos detectados na cena: {classes_str}\n"
            f"Status de Conformidade: {compliance_status}\n"
            f"Alertas de Segurança: {alerts_str}\n"
            f"{sub_details_str}"
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
            return "Nenhum objeto relevante foi detectado na cena analisada."

        encontrados = cls._format_found(class_counts)
        compliance_status = analysis_result.get("compliance_status") or "CONFORME"
        status_text = "Conforme" if compliance_status == "CONFORME" else "Não Conforme (Alerta de Segurança)"

        return f"Análise concluída. Objetos identificados: {encontrados}. Status: {status_text}."

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
            message = self._call_ollama(prompt)
            if not message:
                return self._build_fallback_error_message(error_hint)

            message = re.sub(
                r"\x1b(\[[0-9;?]*[A-Za-z]|[()][AB012]|=|>|~)", "", message
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
            
            # Limpar duplicidades de codificação no português antes de retornar
            return self._clean_duplicate_prefixes(message) if message else self._build_fallback_error_message(error_hint)

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


ollama_message_service = OllamaMessageService()

