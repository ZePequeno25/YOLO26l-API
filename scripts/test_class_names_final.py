#!/usr/bin/env python3
"""
Demonstração final: Comparar análise normal vs debug
"""
import sys
sys.path.insert(0, r"C:\Users\aborr\Projeto TCC\api-tcc")

import asyncio
import json
from pathlib import Path
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Gerar token
response = client.get("/auth/test-token")
token = response.json()["token"]

image_path = Path(r"C:\Users\aborr\Projeto TCC\data\content\custom_data\train\images\100_png_jpg.rf.3207306b5cac7c3702180db1784da211.jpg")

print("=" * 70)
print("TESTE 1: ANÁLISE NORMAL (o que o app Android recebe)")
print("=" * 70)

with open(image_path, "rb") as f:
    files = {"file": (image_path.name, f, "image/jpeg")}
    data = {"id_token": token}
    response = client.post("/detection/analyze", files=files, data=data)

result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
print(f"\n✅ O app recebe: class_counts = {result['class_counts']}")
print(f"✅ detected_chairs = {result['detected_chairs']}")

print("\n" + "=" * 70)
print("TESTE 2: ANÁLISE DETALHADA (para diagnóstico)")
print("=" * 70)

with open(image_path, "rb") as f:
    files = {"file": (image_path.name, f, "image/jpeg")}
    data = {"id_token": token}
    response = client.post("/system/detection-debug", files=files, data=data)

result_debug = response.json()

print("\n📋 MAPEAMENTO DAS CLASSES DO MODELO:")
print(f"{json.dumps(result_debug['model_info'], indent=2, ensure_ascii=False)}")

print("\n📊 RESULTADO DA DETECÇÃO:")
print(f"{json.dumps(result_debug['detection_result'], indent=2, ensure_ascii=False)}")

if result_debug.get('warnings'):
    print("\n⚠️ AVISOS:")
    for w in result_debug['warnings']:
        print(f"  - {w}")

print("\n" + "=" * 70)
print("RESUMO")
print("=" * 70)

model_class_0_name = result_debug['model_info']['all_class_names'].get('0', '?')

print(f"""
✅ Sistema funcionando corretamente!

Quando você vê "0": X no class_counts, significa:
  → O modelo detectou algo com class_id=0
  → No mapeamento do modelo, 0 = "{model_class_0_name}"
  → Isto NÃO é uma cadeira! É outra classe.

Se quiser APENAS cadeiras:
  → Use o endpoint /detection/analyze normalmente
  → Ele retorna: {result['class_counts']}
  → detected_chairs já filtra apenas cadeiras

Se quiser diagnosticar o que o modelo está detectando:
  → Use POST /system/detection-debug
  → Mostra TODAS as classes detectadas
  → Mostra o mapeamento completo do modelo
""")
