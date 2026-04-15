"""
Script de treinamento YOLO para Intel Arc B570 (XPU)
Versão revisada e corrigida - Resolve erro _clear_memory
"""

import argparse
import shutil
import sys
import gc
from pathlib import Path

# ====================== XPU SETUP ======================
try:
    import torch
    XPU_AVAILABLE = torch.xpu.is_available()
except ImportError:
    print("[ERRO] intel_extension_for_pytorch não instalado!")
    print("   Execute: pip install intel-extension-for-pytorch")
    sys.exit(1)

if not XPU_AVAILABLE:
    print("[ERRO] XPU não disponível. Rode o setvars.bat antes de executar!")
    sys.exit(1)
# ======================================================

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api-tcc"))

from app.services.metrics_report_service import metrics_report_service


def parse_args():
    parser = argparse.ArgumentParser(description="Treina YOLO na Arc B570 - Versão Estável")
    parser.add_argument("--model",   default="yolo26l.pt")
    parser.add_argument("--data",    default="data/content/custom_data/data.yaml")
    parser.add_argument("--epochs",  type=int, default=20)
    parser.add_argument("--imgsz",   type=int, default=640)
    parser.add_argument("--batch",   type=int, default=2, help="Mantenha em 2 ou 3")
    parser.add_argument("--name",    default="garrafa")
    parser.add_argument("--half",    action="store_true", default=True)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--fast",    action="store_true")
    return parser.parse_args()


def clear_xpu_memory():
    """Limpeza manual segura para XPU"""
    try:
        torch.xpu.empty_cache()
        gc.collect()
    except:
        pass


def main():
    args = parse_args()

    if args.fast:
        print("[INFO] Preset rápido ativado")
        if args.epochs > 15:
            args.epochs = 10
        if args.batch > 3:
            args.batch = 2

    print(f"\n{'='*120}")
    print("  TREINAMENTO YOLO - Arc B570 (XPU)  →  Versão Estável")
    print(f"  Modelo : {args.model} | Épocas: {args.epochs} | Batch: {args.batch}")
    print(f"  Nome   : {args.name}")
    print(f"{'='*120}\n")

    print(f"[✅] GPU: {torch.xpu.get_device_name(0)}\n")

    from ultralytics import YOLO

    data_path = ROOT / args.data
    if not data_path.exists():
        print(f"[ERRO] data.yaml não encontrado: {data_path}")
        sys.exit(1)

    model = YOLO(args.model)
    xpu_device = torch.device("xpu")

    # Callback para resumo limpo por época
    def on_epoch_end(trainer):
        epoch = trainer.epoch + 1
        total = trainer.epochs
        m = trainer.metrics

        box = m.get('train/box_loss', 0)
        cls = m.get('train/cls_loss', 0)
        dfl = m.get('train/dfl_loss', 0)
        map50 = m.get('metrics/mAP50(B)', 0)
        map95 = m.get('metrics/mAP50-95(B)', 0)

        print(f"📊 Época {epoch:2d}/{total} | "
              f"Box: {box:.4f} | Cls: {cls:.4f} | DFL: {dfl:.4f} | "
              f"mAP50: {map50:.4f} | mAP95: {map95:.4f}")

        clear_xpu_memory()

    model.add_callback("on_fit_epoch_end", on_epoch_end)

    # ==================== TREINAMENTO ====================
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=xpu_device,
        patience=args.patience,
        name=args.name,
        pretrained=True,
        amp=False,
        close_mosaic=10,
        verbose=False,
        workers=2,
        seed=42,
        cache=False,
        plots=False,
        show=False,
        save_period=-1,
    )

    best_pt = Path(results.save_dir) / "weights" / "best.pt"

    clear_xpu_memory()

    # ====================== VALIDAÇÃO ======================
    print("\n" + "="*120)
    print("[INFO] Validando modelo final no XPU...")
    validator = YOLO(str(best_pt))
    val_result = validator.val(
        data=str(data_path),
        imgsz=args.imgsz,
        batch=args.batch,
        device=xpu_device,
        verbose=False,
    )

    # ====================== EXPORTAÇÃO ======================
    print("\n[INFO] Exportando para OpenVINO...")
    ov_dir = model.export(format="openvino", imgsz=640, half=args.half)

    # ====================== COPIA PARA API ======================
    model_dest_dir = ROOT / "models" / args.name
    model_dest_dir.mkdir(parents=True, exist_ok=True)

    ov_dest = model_dest_dir / "my_model_openvino_model"
    if ov_dest.exists():
        shutil.rmtree(ov_dest)
    shutil.copytree(ov_dir, ov_dest)

    shutil.copy2(best_pt, model_dest_dir / "my_model.pt")

    (model_dest_dir / "config.yaml").write_text(
        f'model:\n  name: "{args.name}"\n  path: "my_model.pt"\n  version: "1.0"\n',
        encoding="utf-8"
    )

    print(f"\n{'='*120}")
    print("🎉 TREINAMENTO CONCLUÍDO COM SUCESSO!")
    print(f"   Modelo salvo em → models/{args.name}/")
    print(f"{'='*120}\n")


if __name__ == "__main__":
    main()