"""
intel_yolo_trainer.py
=====================
Biblioteca de treino YOLO com GPU Intel Arc (B570) no Windows.

Detecta e usa automaticamente o melhor backend disponivel:
  1. XPU      -- PyTorch nativo via Level Zero  (torch 2.6.0+xpu)
  2. DirectML -- DirectX 12, instala torch-directml automaticamente
  3. CPU      -- fallback com todos os nucleos disponiveis

Diferenca principal desta biblioteca:
  - Configura as variaveis de ambiente Intel ANTES de importar torch
    (necessario para que Level Zero enumere o dispositivo corretamente).
  - Monkey-patcha select_device() do Ultralytics para aceitar device=xpu
    ou device=directml sem lancar ValueError.
  - Desativa AMP para backends nao-CUDA (evita crashes silenciosos).
  - Workers=0 para DirectML/XPU (multiprocess causa deadlock no Windows).

Uso:
  # Diagnostico -- ver qual backend esta disponivel
  python scripts/intel_yolo_trainer.py --info

  # Treino automatico (autodetect)
  python scripts/intel_yolo_trainer.py --data data/content/custom_data/data.yaml --name garrafa_gpu

  # Forcar DirectML, instalando torch-directml se necessario
  python scripts/intel_yolo_trainer.py --backend directml --install-dml --name garrafa_dml

  # Forcar XPU (requer torch +xpu build e Level Zero enumerando o dispositivo)
  python scripts/intel_yolo_trainer.py --backend xpu --name garrafa_xpu
"""

import argparse
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# -----------------------------------------------------------------------------
# 1.  Variaveis de ambiente Intel devem ser definidas ANTES de importar torch.
#     Se estas variaveis nao estiverem presentes quando o runtime Level Zero
#     e carregado, o dispositivo XPU nao sera enumerado.
# -----------------------------------------------------------------------------

def _configure_intel_env() -> None:
    os.environ.setdefault("ONEAPI_DEVICE_SELECTOR", "level_zero:*")
    os.environ.setdefault("ZE_FLAT_DEVICE_HIERARCHY", "FLAT")
    os.environ.setdefault("SYCL_CACHE_PERSISTENT", "1")
    os.environ.setdefault("ZE_ENABLE_ALT_DRIVERS", "ze_intel_gpu.dll")


_configure_intel_env()

import torch  # importado DEPOIS de configurar o ambiente Intel

# -----------------------------------------------------------------------------
# 2.  Diagnostico de hardware
# -----------------------------------------------------------------------------

def _check_xpu() -> tuple:
    if not hasattr(torch, "xpu"):
        return False, "torch nao compilado com suporte XPU -- precisa do build +xpu"
    if not torch.xpu.is_available():
        count = getattr(torch.xpu, "device_count", lambda: 0)()
        if count == 0:
            return False, (
                "xpu_count=0 -- Level Zero nao enumerou o dispositivo. "
                "Verifique driver Intel Arc e instale o Intel oneAPI Base Toolkit "
                "(https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit.html)"
            )
        return False, "torch.xpu.is_available() = False"
    count = torch.xpu.device_count()
    return True, f"{count} dispositivo(s) XPU"


def _install_directml() -> tuple:
    try:
        import torch_directml  # noqa: F401
        return True, "ja instalado"
    except ImportError:
        pass
    print("[DML] Instalando torch-directml (pode demorar ~30 s)...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "torch-directml", "-q"],
        timeout=180,
        capture_output=False,
    )
    if result.returncode != 0:
        return False, "falha na instalacao -- verifique sua conexao"
    try:
        import torch_directml  # noqa: F401
        return True, "instalado com sucesso"
    except ImportError:
        return False, "instalado mas importacao falhou (conflito de versao de torch?)"


def _check_directml() -> tuple:
    try:
        import torch_directml
        count = torch_directml.device_count()
        if count == 0:
            return False, "torch-directml carregado mas nenhum dispositivo detectado"
        name = torch_directml.device_name(0)
        return True, f"{name} ({count} dispositivo(s))"
    except ImportError:
        return False, "nao instalado -- use --install-dml para instalar"
    except Exception as exc:
        return False, str(exc)


def detect_backend(force=None, install_dml=False):
    """
    Detecta o melhor backend disponivel.

    Retorna (backend_name, device_object) onde backend_name e
    "xpu" | "directml" | "cpu".
    """
    if install_dml and force != "cpu":
        ok, msg = _install_directml()
        print(f"[DML] {msg}")

    xpu_ok, xpu_info = _check_xpu()
    dml_ok, dml_info = _check_directml()

    print("\n+-- Diagnostico de hardware ---------------------------------+")
    print(f"|  torch     : {torch.__version__}")
    print(f"|  XPU       : {'OK' if xpu_ok else 'XX'}  {xpu_info}")
    print(f"|  DirectML  : {'OK' if dml_ok else 'XX'}  {dml_info}")
    print(f"|  CPU       : OK  {os.cpu_count()} nucleos")
    print("+------------------------------------------------------------+\n")

    chosen = force or ("xpu" if xpu_ok else "directml" if dml_ok else "cpu")

    if chosen == "xpu":
        if not xpu_ok:
            print(
                "[AVISO] XPU forcado mas indisponivel. Causas provaveis:\n"
                "  * Driver Intel Arc instalado mas runtime oneAPI ausente.\n"
                "  * Instale: https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit.html\n"
                "  * Usando CPU como fallback.\n"
            )
            chosen = "cpu"
        else:
            device = torch.device("xpu:0")
            print(f"[BACKEND] XPU -- {xpu_info}")
            return "xpu", device

    if chosen == "directml":
        if not dml_ok:
            print(
                f"[AVISO] DirectML forcado mas indisponivel: {dml_info}\n"
                f"  Usando CPU como fallback.\n"
            )
            chosen = "cpu"
        else:
            import torch_directml
            device = torch_directml.device(0)
            print(f"[BACKEND] DirectML -- {dml_info}")
            return "directml", device

    torch.set_num_threads(os.cpu_count() or 8)
    print(f"[BACKEND] CPU -- {os.cpu_count()} threads (Intel Core i7-10700F)")
    return "cpu", torch.device("cpu")


# -----------------------------------------------------------------------------
# 3.  Monkey-patch do Ultralytics
# -----------------------------------------------------------------------------

def patch_ultralytics(backend, device):
    """
    Ultralytics 8.x rejeita qualquer device= que nao seja CPU, CUDA ou MPS.
    Esta funcao substitui select_device() pelo nosso wrapper que aceita
    objetos de device diretamente.

    Para DirectML, tambem desativa chamadas torch.cuda.synchronize() que
    causariam erros durante o training loop.
    """
    if backend == "cpu":
        return

    try:
        import ultralytics.utils.torch_utils as _tu
    except ImportError:
        print("[AVISO] Ultralytics nao encontrado, ignorando patch.")
        return

    _original = _tu.select_device

    _backend_aliases = {
        "xpu": {"xpu", "xpu:0"},
        "directml": {"directml", "dml", "privateuseone", "privateuseone:0"},
    }.get(backend, set())

    def _patched_select(dev="", batch=0, newline=True, verbose=True):
        if dev is device:
            return device
        dev_s = str(dev).lower().strip()
        if dev_s in _backend_aliases or dev_s.startswith(("xpu", "privateuseone")):
            if verbose:
                print(f"[PATCH] select_device({dev!r}) -> {device}")
            return device
        return _original(dev, batch, newline, verbose)

    _tu.select_device = _patched_select

    for mod_name in (
        "ultralytics.engine.trainer",
        "ultralytics.engine.validator",
        "ultralytics.models.yolo.detect.train",
    ):
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "select_device"):
                mod.select_device = _patched_select
        except Exception:
            pass

    if backend == "directml":
        torch.cuda.synchronize = lambda *a, **k: None

        if hasattr(torch, "cuda"):
            # Patch 1: torch.unique(return_counts=True) nao implementado no DirectML.
            # Executa no CPU e devolve tensor no device original.
            _orig_unique = torch.unique

            def _unique_cpu_fallback(
                input,
                sorted=True,
                return_inverse=False,
                return_counts=False,
                dim=None,
            ):
                if return_counts or return_inverse:
                    dev = input.device
                    result = _orig_unique(
                        input.cpu(),
                        sorted=sorted,
                        return_inverse=return_inverse,
                        return_counts=return_counts,
                        dim=dim,
                    )
                    if isinstance(result, tuple):
                        return tuple(r.to(dev) for r in result)
                    return result.to(dev)
                return _orig_unique(input, sorted=sorted, dim=dim)

            torch.unique = _unique_cpu_fallback
            print("[PATCH] torch.unique CPU fallback ativado para DirectML")

            # Patch 2: scatter_add_ nao implementado corretamente no DirectML.
            # Delega ao CPU in-place.
            _orig_scatter_add_ = torch.Tensor.scatter_add_

            def _scatter_add_fallback(self, dim, index, src):
                dev = self.device
                dev_str = str(dev)
                if dev_str.startswith("privateuseone") or "dml" in dev_str.lower():
                    cpu_result = self.cpu().scatter_add_(dim, index.cpu(), src.cpu())
                    self.copy_(cpu_result.to(dev))
                    return self
                return _orig_scatter_add_(self, dim, index, src)

            torch.Tensor.scatter_add_ = _scatter_add_fallback
            print("[PATCH] scatter_add_ CPU fallback ativado para DirectML")

    print(f"[PATCH] Ultralytics patcheado para backend '{backend}'")


# -----------------------------------------------------------------------------
# 4.  Treinamento
# -----------------------------------------------------------------------------

def train(args, backend, device):
    from ultralytics import YOLO

    data_path = ROOT / args.data
    if not data_path.exists():
        print(f"[ERRO] data.yaml nao encontrado: {data_path}")
        sys.exit(1)

    # AMP (mixed precision) so estavel em CUDA nativo; causa crash em DirectML
    amp = backend == "xpu"

    # Workers >0 causa deadlock em DirectML/XPU no Windows (multiprocessing)
    workers = 0 if backend in ("directml", "xpu") else min(4, os.cpu_count() or 4)

    model_name = Path(str(args.model)).name.lower()
    train_batch = args.batch
    train_imgsz = args.imgsz

    # Limite conservador para modelos 26l no DirectML (VRAM Intel Arc).
    if backend == "directml" and "26l" in model_name:
        train_batch = min(train_batch, 4)
        train_imgsz = min(train_imgsz, 384)
        print("[LIMIT] Modelo 26l detectado: aplicando limite inicial batch<=4 e imgsz<=384")

    print(f"\n{'='*62}")
    print(f"  INTEL YOLO TRAINER")
    print(f"  Modelo base : {args.model}")
    print(f"  Backend     : {backend.upper()}")
    print(f"  Dataset     : {args.data}")
    print(f"  Epocas      : {args.epochs}")
    print(f"  Batch       : {train_batch}")
    print(f"  Imgsz       : {train_imgsz}")
    print(f"  Patience    : {args.patience}")
    print(f"  AMP         : {amp}")
    print(f"  Workers     : {workers}")
    print(f"  Nome saida  : {args.name}")
    print(f"{'='*62}\n")

    model = YOLO(args.model)

    # Planos de retry para OOM no DirectML.
    retry_plan = [(train_batch, train_imgsz)]
    if backend == "directml":
        fallback_plan = [(2, 320), (1, 320), (1, 256)]
        for b, s in fallback_plan:
            if (b, s) not in retry_plan and (b <= train_batch or s <= train_imgsz):
                retry_plan.append((b, s))

    results = None
    last_exc = None
    for attempt_idx, (attempt_batch, attempt_imgsz) in enumerate(retry_plan, start=1):
        try:
            print(f"[TRAIN] Tentativa {attempt_idx}/{len(retry_plan)}: batch={attempt_batch}, imgsz={attempt_imgsz}")
            results = model.train(
                data=str(data_path),
                epochs=args.epochs,
                imgsz=attempt_imgsz,
                batch=attempt_batch,
                device=device,
                patience=args.patience,
                name=args.name,
                pretrained=True,
                amp=amp,
                close_mosaic=10,
                workers=workers,
                verbose=True,
                exist_ok=True,
            )
            break
        except RuntimeError as exc:
            msg = str(exc).lower()
            is_oom = (
                "not enough gpu video memory" in msg
                or "out of memory" in msg
                or "could not allocate tensor" in msg
            )
            if not is_oom or attempt_idx == len(retry_plan):
                raise
            last_exc = exc
            print(f"[OOM] Falha por VRAM na tentativa {attempt_idx}. Reduzindo batch/imgsz e tentando novamente...")

    if results is None and last_exc is not None:
        raise last_exc

    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if not best_pt.exists():
        print(f"[ERRO] best.pt nao encontrado em {results.save_dir}")
        sys.exit(1)

    print(f"\n[OK] Treino concluido -- melhor modelo: {best_pt}")
    return best_pt, str(results.save_dir)


# -----------------------------------------------------------------------------
# 5.  Exportacao OpenVINO
# -----------------------------------------------------------------------------

def export_openvino(best_pt, half=False):
    from ultralytics import YOLO

    print(f"\n[EXPORT] Exportando {best_pt.name} -> OpenVINO (FP16={half})...")
    model = YOLO(str(best_pt))
    export_path = model.export(format="openvino", imgsz=640, half=half, int8=False)
    ov_dir = Path(export_path)
    print(f"[OK] OpenVINO: {ov_dir}")
    return ov_dir


def copy_to_models(ov_dir, name):
    dest = ROOT / "models" / name
    dest.mkdir(parents=True, exist_ok=True)

    ov_dest = dest / "my_model_openvino_model"
    if ov_dest.exists():
        shutil.rmtree(ov_dest)
    shutil.copytree(ov_dir, ov_dest)

    src_pt = ov_dir.parent / "best.pt"
    if src_pt.exists():
        shutil.copy2(src_pt, dest / "my_model.pt")

    (dest / "config.yaml").write_text(
        f'model:\n  name: "{name}"\n  path: "my_model.pt"\n  version: "1.0"\n',
        encoding="utf-8",
    )
    print(f"[OK] Copiado para models/{name}/")
    return ov_dest


# -----------------------------------------------------------------------------
# 6.  CLI
# -----------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Treino YOLO com Intel Arc -- DirectML / XPU / CPU",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Checar o que esta disponivel no seu sistema:
  python scripts/intel_yolo_trainer.py --info

  # Treino automatico (melhor backend detectado):
  python scripts/intel_yolo_trainer.py --data data/content/custom_data/data.yaml --name garrafa_gpu

  # Forcar DirectML (instala torch-directml se necessario):
  python scripts/intel_yolo_trainer.py --backend directml --install-dml --name garrafa_dml

  # Para DirectML funcionar melhor, use a venv dedicada:
  powershell -ExecutionPolicy Bypass -File scripts/setup_directml_venv.ps1
  .venv-dml\\Scripts\\python.exe scripts/intel_yolo_trainer.py --backend directml --name garrafa_dml
""",
    )
    p.add_argument("--model", default="models/yolo26l.pt",
                   help="Modelo base YOLO (padrao: models/yolo26l.pt)")
    p.add_argument("--data", default="data/content/custom_data/data.yaml",
                   help="Caminho para data.yaml do dataset")
    p.add_argument("--epochs", type=int, default=35)
    p.add_argument("--imgsz", type=int, default=512,
                   help="Tamanho das imagens (512 = mais rapido, 640 = mais preciso)")
    p.add_argument("--batch", type=int, default=16,
                   help="Batch size -- reduza para 8 se der erro de memoria")
    p.add_argument("--name", default="garrafa_intel",
                   help="Nome do modelo de saida em models/")
    p.add_argument("--patience", type=int, default=8,
                   help="Early stopping: parar apos N epocas sem melhoria")
    p.add_argument("--half", action="store_true",
                   help="Exportar OpenVINO em FP16 (recomendado para inferencia Arc)")
    p.add_argument("--backend", choices=["xpu", "directml", "cpu"], default=None,
                   help="Forcar backend especifico (padrao: autodetect xpu->dml->cpu)")
    p.add_argument("--install-dml", action="store_true",
                   help="Instalar torch-directml automaticamente se nao estiver presente")
    p.add_argument("--info", action="store_true",
                   help="Exibir diagnostico de hardware e sair")
    return p.parse_args()


def main():
    args = parse_args()

    if args.info:
        detect_backend(install_dml=False)
        return

    backend, device = detect_backend(
        force=args.backend,
        install_dml=args.install_dml,
    )
    patch_ultralytics(backend, device)

    best_pt, save_dir = train(args, backend, device)
    ov_dir = export_openvino(best_pt, half=args.half)
    copy_to_models(ov_dir, args.name)

    print(f"\n{'='*62}")
    print(f"  CONCLUIDO -- Backend: {backend.upper()}")
    print(f"  Treino   : {save_dir}")
    print(f"  Modelo   : models/{args.name}/")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
