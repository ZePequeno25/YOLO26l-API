#!/usr/bin/env python3
"""
Teste completo da API com logging detalhado
"""
import sys
sys.path.insert(0, r"C:\Users\aborr\Projeto TCC\api-tcc")

import asyncio
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Importar a app
from main import app
client = TestClient(app)

# Teste 1: Gerar token válido
print("=" * 60)
print("TESTE 1: Gerar token válido")
print("=" * 60)

response = client.get("/auth/test-token")
print(f"Status: {response.status_code}")
result = response.json()
print(f"Response: {json.dumps(result, indent=2)}")

if response.status_code == 200:
    token = result["token"]
    print(f"✅ Token gerado: {token[:30]}...")
else:
    print("❌ Falha ao gerar token")
    sys.exit(1)

# Teste 2: Análise de imagem com cadeiras
print("\n" + "=" * 60)
print("TESTE 2: Análise de imagem com cadeiras")
print("=" * 60)

image_path = Path(r"C:\Users\aborr\Projeto TCC\content\custom_data\train\images\100_png_jpg.rf.3207306b5cac7c3702180db1784da211.jpg")

with open(image_path, "rb") as f:
    files = {"file": (image_path.name, f, "image/jpeg")}
    data = {"id_token": token}
    response = client.post("/detection/analyze", files=files, data=data)

print(f"Status: {response.status_code}")
result = response.json()
print(f"\n📊 Response completo:")
print(json.dumps(result, indent=2, ensure_ascii=False))

# Análise
print(f"\n📋 Análise:")
print(f"  ✅ Sucesso: {result.get('success')}")
print(f"  📝 Mensagem: {result.get('message')}")
print(f"  🪑 Cadeiras detectadas: {result.get('detected_chairs')}")
print(f"  📦 Todas as classes: {result.get('class_counts')}")

if result.get('detected_chairs') > 0:
    print(f"  ✅ Detecção funcionando corretamente!")
else:
    print(f"  ⚠️ Aviso: Nenhuma cadeira detectada nesta imagem")

# Verificar se há classe "0"
if "0" in result.get('class_counts', {}):
    print(f"  ⚠️ PROBLEMA: Classe '0' foi detectada: {result['class_counts']['0']}")
    print(f"     Isso significa que o modelo detectou algo com classe_id=0")
    print(f"     Modelo.names[0] = '0' (parece ser um problema no treino do modelo)")
