"""
Script de treinamento de novo modelo YOLO com exportação automática para OpenVINO.

Uso:
    python scripts/train_new_model.py --model yolo11s.pt --data data/content/custom_data/data.yaml
                                      --epochs 100 --name meu_modelo

Após treinar, o script exporta automaticamente para OpenVINO e copia o modelo
para api-tcc/models/ pronto para uso com a Intel Arc B570.
"""

import argparse
import shutil
import sys
from pathlib import Path

# Garante que imports funcionam mesmo rodando da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def parse_args():
    parser = argparse.ArgumentParser(description="Treina YOLO e exporta para OpenVINO")
    parser.add_argument("--model",   default="yolo26l.pt",
                        help="Modelo base YOLO (ex: yolo11s.pt, yolo11m.pt, yolov8n.pt)")
    parser.add_argument("--data",    default="data/content/custom_data/data.yaml",
                        help="Caminho para o data.yaml do dataset")
    parser.add_argument("--epochs",  type=int, default=100)
    parser.add_argument("--imgsz",   type=int, default=640)
    parser.add_argument("--batch",   type=int, default=8,
                        help="Tamanho do batch. Reduza se der OOM na GPU.")
    parser.add_argument("--name",    default="novo_modelo",
                        help="Nome da pasta de saída do treinamento")
    parser.add_argument("--device",  default=None,
                        help="Dispositivo de treino: 0 (GPU CUDA), 'xpu' (Intel Arc via IPEX), "
                             "cpu. Se vazio, detecta automaticamente.")
    parser.add_argument("--half",    action="store_true",
                        help="Usar FP16 durante exportação OpenVINO (recomendado para Arc)")
    parser.add_argument("--patience", type=int, default=30,
                        help="Early stopping: parar após N epocas sem melhoria")
    parser.add_argument("--fast", action="store_true",
                        help="Ativa preset rapido para iterar mais cedo (bom para datasets grandes)")
    return parser.parse_args()


def apply_fast_preset(args):
    """Aplica valores mais rápidos para um primeiro treino de validação."""
    if not args.fast:
        return args

    # Ajusta apenas quando o usuário manteve o default atual, evitando sobrescrever escolhas explícitas.
    if args.model == "yolo26l.pt":
        args.model = "yolo11n.pt"
    if args.epochs == 100:
        args.epochs = 35
    if args.imgsz == 640:
        args.imgsz = 512
    if args.batch == 8:
        args.batch = 16
    if args.patience == 30:
        args.patience = 8

    return args


def detect_best_device():
    """Detecta automaticamente o melhor dispositivo disponível."""
    # 1. Tentar Intel Arc via IPEX (XPU)
    try:
        import intel_extension_for_pytorch as ipex  # noqa: F401
        import torch
        if torch.xpu.is_available():
            device_count = torch.xpu.device_count()
            print(f"[INFO] Intel Arc detectada via IPEX: {device_count} dispositivo(s) XPU")
            return "xpu"
    except ImportError:
        pass

    # 2. Tentar CUDA
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            print(f"[INFO] GPU CUDA detectada: {name}")
            return "0"
    except Exception:
        pass

    print("[AVISO] Nenhuma GPU detectada — usando CPU (treinamento mais lento)")
    return "cpu"


def train(args):
    from ultralytics import YOLO

    device = args.device or detect_best_device()

    data_path = ROOT / args.data
    if not data_path.exists():
        print(f"[ERRO] data.yaml não encontrado: {data_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  TREINAMENTO YOLO")
    print(f"  Modelo base : {args.model}")
    print(f"  Dataset     : {data_path}")
    print(f"  Épocas      : {args.epochs}")
    print(f"  Batch       : {args.batch}")
    print(f"  Imgsz       : {args.imgsz}")
    print(f"  Dispositivo : {device}")
    print(f"  Nome saída  : {args.name}")
    print(f"{'='*60}\n")

    model = YOLO(args.model)

    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        patience=args.patience,
        name=args.name,
        pretrained=True,
        amp=True,          # mixed precision (acelera em GPU)
        close_mosaic=10,
        verbose=True,
    )

    # Caminho do melhor modelo treinado
    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if not best_pt.exists():
        print(f"[ERRO] best.pt não encontrado em {results.save_dir}")
        sys.exit(1)

    print(f"\n[OK] Treinamento concluído. Melhor modelo: {best_pt}")
    return best_pt, results.save_dir


def export_openvino(best_pt: Path, half: bool):
    """Exporta o modelo .pt para formato OpenVINO."""
    from ultralytics import YOLO

    print(f"\n{'='*60}")
    print(f"  EXPORTANDO PARA OPENVINO")
    print(f"  Origem  : {best_pt}")
    print(f"  FP16    : {half}")
    print(f"{'='*60}\n")

    model = YOLO(str(best_pt))

    # Exporta para a pasta ao lado do best.pt
    export_path = model.export(
        format="openvino",
        imgsz=640,
        half=half,      # FP16 recomendado para Intel Arc
        int8=False,
    )

    ov_dir = Path(export_path)
    print(f"\n[OK] Exportação OpenVINO concluída: {ov_dir}")
    return ov_dir


def copy_to_api(ov_dir: Path, model_name: str):
    """
    Copia o modelo para ROOT/models/{model_name}/ (onde a DetectionService procura).
    A DetectionService lê os .pt de ROOT/models/{model_name}/*.pt e o OpenVINO de
    ROOT/models/{model_name}/my_model_openvino_model/.
    """
    model_dest_dir = ROOT / "models" / model_name
    model_dest_dir.mkdir(parents=True, exist_ok=True)

    # Copiar pasta OpenVINO
    ov_dest = model_dest_dir / "my_model_openvino_model"
    if ov_dest.exists():
        shutil.rmtree(ov_dest)
    shutil.copytree(ov_dir, ov_dest)

    # Copiar best.pt
    best_src = ov_dir.parent / "best.pt"
    if best_src.exists():
        shutil.copy2(best_src, model_dest_dir / "my_model.pt")

    # Criar config.yaml mínimo para a API
    cfg = model_dest_dir / "config.yaml"
    cfg.write_text(
        f"model:\n  name: \"{model_name}\"\n  path: \"my_model.pt\"\n"
        f"  version: \"1.0\"\n",
        encoding="utf-8",
    )

    print(f"\n[OK] Modelo copiado para: {model_dest_dir}")
    print(f"     Para usar na API: POST /detection/analyze com model={model_name}")
    return ov_dest


def main():
    args = parse_args()
    args = apply_fast_preset(args)

    if args.fast:
        print("[INFO] Preset rapido ativado (--fast)")
        print("       Dica: para mais qualidade final, rode um segundo treino com imgsz 640.")

    best_pt, save_dir = train(args)
    ov_dir = export_openvino(best_pt, half=args.half)
    copy_to_api(ov_dir, args.name)

    print(f"\n{'='*60}")
    print(f"  PRONTO!")
    print(f"  Treino    : {save_dir}")
    print(f"  OpenVINO  : {ov_dir}")
    print(f"  API       : api-tcc/models/{args.name}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
