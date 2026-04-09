# =============================================================
# Instalação de dependências para tentar treino com Intel Arc B570
# usando PyTorch XPU em venv Python 3.12 (Windows)
# =============================================================

$ErrorActionPreference = "Stop"

Write-Host "[INFO] Criando ambiente virtual .venv-xpu (Python 3.12)..."
py -3.12 -m venv .venv-xpu

$Py = ".\.venv-xpu\Scripts\python.exe"

Write-Host "[INFO] Atualizando ferramentas de empacotamento..."
& $Py -m pip install --upgrade pip setuptools wheel

Write-Host "[INFO] Instalando PyTorch XPU (Intel)..."
& $Py -m pip install torch==2.6.0+xpu torchvision==0.21.0+xpu torchaudio==2.6.0+xpu --index-url https://download.pytorch.org/whl/xpu

Write-Host "[INFO] Instalando Ultralytics..."
& $Py -m pip install -U ultralytics

Write-Host "[INFO] Validando runtime XPU..."
& $Py -c "import torch; print('torch:', torch.__version__); print('xpu_available:', torch.xpu.is_available()); print('xpu_count:', torch.xpu.device_count() if torch.xpu.is_available() else 0)"

Write-Host "`n[OK] Ambiente criado em .venv-xpu"
Write-Host "[INFO] Para treinar com esse ambiente, use:"
Write-Host "      .\.venv-xpu\Scripts\python.exe scripts/train_new_model.py --data data/content/custom_data/data.yaml --device cpu --name garrafa_fast --fast"
Write-Host "[AVISO] No Ultralytics atual, --device xpu ainda nao e aceito diretamente; se xpu_count for 0, revise drivers/oneAPI."
