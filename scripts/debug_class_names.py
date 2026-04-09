#!/usr/bin/env python3
"""
Debug para verificar como o modelo retorna os nomes das classes
"""
import sys
sys.path.insert(0, r"C:\Users\aborr\Projeto TCC\api-tcc")

from config.settings import settings
from ultralytics import YOLO

model = YOLO(settings.MODEL_PATH)

print("🔍 DEBUG - Nomes das Classes do Modelo\n")
print(f"Model names type: {type(model.names)}")
print(f"Model names: {model.names}")
print(f"Model names keys: {list(model.names.keys()) if isinstance(model.names, dict) else 'N/A'}")
print(f"Model names values: {list(model.names.values()) if isinstance(model.names, dict) else 'N/A'}")

print("\nTestando acesso:")
try:
    print(f"  model.names[0] = {model.names[0]}")
    print(f"  model.names.get(0) = {model.names.get(0) if isinstance(model.names, dict) else 'N/A'}")
except Exception as e:
    print(f"  Erro: {e}")

# Simular uma detecção para ver o que vem
print("\n🧪 Testando com uma imagem...")
results = model("content/custom_data/train/images/100_png_jpg.rf.3207306b5cac7c3702180db1784da211.jpg", verbose=False)

if results and len(results[0].boxes) > 0:
    result = results[0]
    print(f"\nPrimeiro resultado:")
    print(f"  Classes detectadas (indices): {result.boxes.cls.tolist()}")
    print(f"  Result.names type: {type(result.names)}")
    print(f"  Result.names: {result.names}")
    
    print(f"\nMapeamento de classes:")
    for idx in set(result.boxes.cls.tolist()):
        idx_int = int(idx)
        try:
            class_name = result.names[idx_int]
            print(f"  Índice {idx_int} -> '{class_name}'")
        except Exception as e:
            print(f"  Índice {idx_int} -> Erro: {e}")
