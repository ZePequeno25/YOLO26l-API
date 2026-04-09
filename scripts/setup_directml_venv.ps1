# =============================================================
# setup_directml_venv.ps1
# Cria .venv-dml com torch padrão + torch-directml + ultralytics.
#
# Por que um venv separado?
#   torch-directml requer torch do PyPI (sem o sufixo +xpu).
#   Misturar com o build +xpu causa conflito de DLL.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts/setup_directml_venv.ps1
#
# Após terminar, treinar com:
#   .\.venv-dml\Scripts\python.exe scripts/intel_yolo_trainer.py `
#       --backend directml `
#       --data data/content/custom_data/data.yaml `
#       --name garrafa_dml
# =============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$VenvDir = ".venv-dml"
$Py = ".\$VenvDir\Scripts\python.exe"

Write-Host "[1/5] Criando ambiente virtual Python 3.12 em $VenvDir..."
if (Test-Path $VenvDir) {
    Write-Host "      Removendo venv anterior..."
    Remove-Item -Recurse -Force $VenvDir
}
py -3.12 -m venv $VenvDir

Write-Host "[2/5] Atualizando pip/setuptools/wheel..."
& $Py -m pip install --upgrade pip setuptools wheel -q

Write-Host "[3/5] Instalando PyTorch (versão padrão PyPI, sem +xpu)..."
& $Py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu -q

Write-Host "[4/5] Instalando torch-directml (DirectX 12 - Intel/AMD/NVIDIA)..."
& $Py -m pip install torch-directml -q

Write-Host "[5/5] Instalando Ultralytics..."
& $Py -m pip install ultralytics -q

Write-Host ""
Write-Host "[Validando ambiente DirectML]"
$validScript = 'import torch; import torch_directml; count = torch_directml.device_count(); print("  torch            :", torch.__version__); print("  dml device count :", count); [print("  dml[" + str(i) + "]           :", torch_directml.device_name(i)) for i in range(count)]; print("  AVISO: nenhum dispositivo DirectML detectado." if count == 0 else "  OK: DirectML pronto para treino!")'
& $Py -c $validScript

Write-Host ""
Write-Host "======================================================="
Write-Host "  Configuracao concluida!"
Write-Host ""
Write-Host "  Para verificar o ambiente:"
Write-Host "    .\.venv-dml\Scripts\python.exe scripts/intel_yolo_trainer.py --info"
Write-Host ""
Write-Host "  Para treinar com GPU Intel Arc (DirectML):"
Write-Host "    .\.venv-dml\Scripts\python.exe scripts/intel_yolo_trainer.py ``"
Write-Host "        --backend directml ``"
Write-Host "        --data data/content/custom_data/data.yaml ``"
Write-Host "        --name garrafa_dml"
Write-Host "======================================================="
