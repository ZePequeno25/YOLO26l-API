import os
from pathlib import Path

def main():
    current_dir = Path(__file__).resolve().parent
    models_dir = current_dir.parent / "models"
    
    if not models_dir.exists():
        with open(current_dir / "models_status.txt", "w", encoding="utf-8") as out:
            out.write("ERROR: models directory not found")
        return

    folders = [f for f in models_dir.iterdir() if f.is_dir() and not f.name.startswith('.')]
    results = []
    
    for f in sorted(folders, key=lambda x: x.name.lower()):
        has_pt = len(list(f.glob("*.pt"))) > 0
        ov_folders = list(f.glob("*_openvino_model"))
        has_ov = len(ov_folders) > 0
        
        status = "Convertido (FP16)" if has_ov else "Apenas PyTorch (.pt)"
        results.append(f"- **{f.name}**: {status}")

    with open(current_dir / "models_status.txt", "w", encoding="utf-8") as out:
        out.write("\n".join(results))

if __name__ == "__main__":
    main()
