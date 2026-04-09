#!/usr/bin/env python3
"""
Script simples para testar a API e ver o mapeamento de classes
Use este script para diagnosticar problemas
"""
import requests
import json
import sys
from pathlib import Path

# Configuração
API_BASE_URL = "http://localhost:8000"
IMAGE_PATH = Path(r"C:\Users\aborr\Projeto TCC\content\custom_data\train\images\100_png_jpg.rf.3207306b5cac7c3702180db1784da211.jpg")

def test_api():
    print("=" * 70)
    print("🧪 TESTE DE APIs DE DETECÇÃO")
    print("=" * 70)
    
    # 1. Gerar token
    print("\n[1/3] Gerando token...")
    resp = requests.get(f"{API_BASE_URL}/auth/test-token")
    if resp.status_code != 200:
        print(f"❌ Erro ao gerar token: {resp.status_code}")
        return
    
    token = resp.json()["token"]
    print(f"✅ Token gerado: {token[:30]}...")
    
    # 2. Teste Detecção Normal
    print("\n[2/3] Testando análise normal (POST /detection/analyze)...")
    
    with open(IMAGE_PATH, "rb") as f:
        files = {"file": (IMAGE_PATH.name, f, "image/jpeg")}
        data = {"id_token": token}
        resp = requests.post(f"{API_BASE_URL}/detection/analyze", files=files, data=data)
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ Status: 200 OK")
        print(f"   Classes detectadas: {result['class_counts']}")
        print(f"   Cadeiras: {result['detected_chairs']}")
        print(f"   Resposta completa:")
        print(f"   {json.dumps(result, indent=6, ensure_ascii=False)}")
    else:
        print(f"❌ Erro: {resp.status_code}")
        print(f"   {resp.text}")
        return
    
    # 3. Teste Debug
    print("\n[3/3] Testando análise detalhada (POST /system/detection-debug)...")
    
    with open(IMAGE_PATH, "rb") as f:
        files = {"file": (IMAGE_PATH.name, f, "image/jpeg")}
        data = {"id_token": token}
        resp = requests.post(f"{API_BASE_URL}/system/detection-debug", files=files, data=data)
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ Status: 200 OK")
        print(f"\n📋 Mapeamento de classes do modelo:")
        print(json.dumps(result['model_info']['all_class_names'], indent=4))
        print(f"\n📊 Classes detectadas:")
        print(json.dumps(result['detection_result']['detected_classes'], indent=4))
        
        if result.get('warnings'):
            print(f"\n⚠️ Avisos:")
            for w in result['warnings']:
                print(f"   - {w}")
    else:
        print(f"❌ Erro: {resp.status_code}")
        print(f"   {resp.text}")
    
    print("\n" + "=" * 70)
    print("✅ INTERPRETAÇÃO:")
    print("=" * 70)
    print("""
    Se vir {"0": X} na resposta, significa:
    - O modelo detectou a classe 0 (que foi rotulada como "0" no treinamento)
    - Isto não é uma cadeira!
    - Verifique o mapeamento de classes em model_info para entender
    
    Se vir {"chair": X}, significa:
    - Cadeiras foram detectadas corretamente ✅
    """)

if __name__ == "__main__":
    # Verificar se API está rodando
    try:
        resp = requests.get(f"{API_BASE_URL}/system/status", timeout=2)
        print(f"✅ API está rodando em {API_BASE_URL}\n")
    except:
        print(f"❌ API não está respondendo em {API_BASE_URL}")
        print(f"   Inicie a API com: python main.py")
        sys.exit(1)
    
    # Verificar se imagem existe
    if not IMAGE_PATH.exists():
        print(f"❌ Imagem de teste não encontrada: {IMAGE_PATH}")
        sys.exit(1)
    
    # Executar teste
    test_api()
