import os
import sys
from pathlib import Path

# Adiciona o diretório scripts ao sys.path
root_dir = Path(__file__).resolve().parent.parent
scripts_dir = root_dir / "scripts"
sys.path.insert(0, str(scripts_dir))

from organize_models import organize_models

if __name__ == "__main__":
    print("🚀 Executando organizador de modelos YOLO...")
    organize_models()
    print("✅ Concluído com sucesso!")
