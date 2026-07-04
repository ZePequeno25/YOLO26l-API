"""
Settings configuration module for the API.
Handles loading environment variables and configuring default parameters.
"""
from pathlib import Path

from pydantic_settings import BaseSettings
import torch


def _detect_inference_device() -> str:
    """Detecta o melhor dispositivo de inferência disponível (GPU Intel via OpenVINO -> CUDA -> CPU)."""
    # 1. Tentar GPU dedicada/integrada Intel via OpenVINO
    try:
        from openvino.runtime import Core
        core = Core()
        if "GPU" in core.available_devices:
            print("🚀 Intel GPU detectada para inferência OpenVINO.")
            return "GPU"
    except Exception:
        pass

    # 2. Tentar NVIDIA CUDA
    try:
        if torch.cuda.is_available():
            print("🚀 NVIDIA GPU (CUDA) detectada para inferência.")
            return "cuda"
    except Exception:
        pass

    print("ℹ️ Usando CPU para inferência.")
    return "cpu"


# pylint: disable=too-few-public-methods
class Settings(BaseSettings):
    """
    Application settings container loaded from environment variables or defaults.
    """
    MODEL_PATH: str = str(
        Path(__file__).parent.parent.parent / "models" / "cadeira" / "my_model.pt"
    )
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = True
    DETECTION_CONF_THRESHOLD: float = 0.65
    DETECTION_IOU_THRESHOLD: float = 0.35
    COUNT_DEDUP_IOU_THRESHOLD: float = 0.5
    SAVE_TRAINING_ARTIFACTS: bool = False
    SAVE_PREDICTION_FILES: bool = False
    TRAINING_ARTIFACTS_DIR: str = str(
        Path(__file__).parent.parent.parent / "training_artifacts"
    )
    ENABLE_PERSONALIZED_MESSAGE: bool = True
    OLLAMA_COMMAND: str = "ollama"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_TIMEOUT_SECONDS: int = 120
    ALLOW_TEST_ADMIN_BYPASS_TOKEN: bool = False
    ADMIN_BYPASS_TOKEN: str = ""
    TEST_JWT_SECRET: str = ""
    API_JWT_SECRET: str = ""
    API_JWT_EXPIRE_HOURS: int = 24
    CORS_ALLOWED_ORIGINS: str = (
        "http://localhost,http://127.0.0.1,https://kelvin-tech-api.online"
    )
    ALLOWED_HOSTS: str = "*"

    # Proteção contra escaneamento de rotas inexistentes
    NOT_FOUND_MAX_HITS: int = 4         # bloqueia no 4o 404 dentro da janela
    NOT_FOUND_WINDOW_SECONDS: int = 1   # janela curta para detectar rajadas
    NOT_FOUND_BLOCK_SECONDS: int = 300  # duração do bloqueio em segundos

    # Firebase App Check
    ENABLE_APP_CHECK: bool = False      # habilitar validação de App Check em produção

    # Rate limiting para rotas de autenticação (evitar abuso de envio de e-mail)
    AUTH_RATE_LIMIT_MAX: int = 5        # máx. requisições na janela
    AUTH_RATE_LIMIT_WINDOW: int = 60    # janela em segundos
    AUTH_RATE_LIMIT_BLOCK: int = 300    # duração do bloqueio em segundos

    # Proteção global anti-rajada / anti-DDoS na camada da aplicação
    GLOBAL_RATE_LIMIT_MAX: int = 60     # máximo de requisições por IP na janela
    GLOBAL_RATE_LIMIT_WINDOW: int = 10  # janela curta para detectar rajadas gerais
    GLOBAL_RATE_LIMIT_BLOCK: int = 300  # bloqueio do IP por excesso de tráfego
    GLOBAL_PERMANENT_BLACKLIST_ON_BURST: bool = True
    PERMANENT_BLACKLIST_FILE: str = str(
        Path(__file__).parent.parent / "logs" / "security" / "permanent_blacklist.txt"
    )
    ENABLE_ADMIN_HONEYPOT: bool = True
    ADMIN_HONEYPOT_PATHS: str = (
        "/admin,/admin/,/admin-panel,/administrator,/wp-admin,/phpmyadmin"
    )
    BLOCK_LOCAL_REQUESTS: bool = True

    # Limite de tamanho do corpo da requisição
    MAX_REQUEST_BODY_BYTES: int = 52428800  # 50 MB

    # Limite de duração de vídeo enviado para análise
    MAX_VIDEO_DURATION_SECONDS: int = 30

    # Processa 1 frame a cada N frames em vídeo para reduzir latência/timeout no proxy.
    VIDEO_INFERENCE_STRIDE: int = 2

    # Configuração automática de dispositivo (OpenVINO GPU -> CUDA -> CPU)
    INFERENCE_DEVICE: str = _detect_inference_device()

    class Config:
        """Pydantic config subclass to define environment variables source."""
        env_file = ".env"


settings = Settings()
