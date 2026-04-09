#!/usr/bin/env python3
"""
Script para inspecionar as classes de um modelo YOLO.
Uso: python inspect_model_classes.py <caminho_para_modelo.pt>
"""

import sys
from pathlib import Path
from ultralytics import YOLO

def main():
    if len(sys.argv) != 2:
        print("Uso: python inspect_model_classes.py <caminho_para_modelo.pt>")
        sys.exit(1)

    model_path = sys.argv[1]

    if not Path(model_path).exists():
        print(f"Erro: Arquivo {model_path} não encontrado.")
        sys.exit(1)

    try:
        print(f"Carregando modelo: {model_path}")
        model = YOLO(model_path)
        print("Classes encontradas:")
        for idx, name in model.names.items():
            print(f"  {idx}: {name}")
        print(f"\nTotal de classes: {len(model.names)}")
    except Exception as e:
        print(f"Erro ao carregar o modelo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()