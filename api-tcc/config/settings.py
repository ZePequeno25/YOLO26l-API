from pydantic_settings import BaseSettings
from pathlib import Path
import torch

class Settings(BaseSettings):
    MODEL_PATH: str = str(Path(__file__).parent.parent.parent / "models" / "chair" / "my_model.pt")
    HOST: str = "192.168.76.103"
    PORT: int = 8000
    DEBUG: bool = True
    DETECTION_CONF_THRESHOLD: float = 0.65
    DETECTION_IOU_THRESHOLD: float = 0.35
    COUNT_DEDUP_IOU_THRESHOLD: float = 0.5
    SAVE_TRAINING_ARTIFACTS: bool = True
    TRAINING_ARTIFACTS_DIR: str = str(Path(__file__).parent.parent.parent / "training_artifacts")
    ENABLE_PERSONALIZED_MESSAGE: bool = True
    OLLAMA_COMMAND: str = "ollama"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_TIMEOUT_SECONDS: int = 20
    ALLOW_TEST_ADMIN_BYPASS_TOKEN: bool = False
    ADMIN_BYPASS_TOKEN: str = ""
    TEST_JWT_SECRET: str = ""
    
    # Configuração automática de dispositivo
    INFERENCE_DEVICE: str = "CPU" if torch.cuda.is_available() else "cpu"

    class Config:
        env_file = ".env"

settings = Settings()