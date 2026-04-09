#!/usr/bin/env python3
"""
Script para testar upload de imagem via requests (simulando o comportamento da API)
"""
import requests
import os
from pathlib import Path

def test_upload_simulation():
    """Simula o upload de uma imagem para testar se o problema é no cliente ou servidor"""
    print("🔍 TESTE DE UPLOAD SIMULADO\n")

    # URL da API (ajuste se necessário)
    base_url = "http://localhost:8000"

    # Procurar uma imagem de teste
    test_images = list(Path("content/custom_data/train/images").glob("*.jpg"))
    if not test_images:
        print("❌ Nenhuma imagem de teste encontrada")
        return

    test_image = test_images[0]
    print(f"📁 Usando imagem de teste: {test_image}")
    print(f"   Tamanho: {os.path.getsize(test_image)} bytes")

    # Primeiro testar a rota de diagnóstico
    try:
        response = requests.get(f"{base_url}/system/diagnostic")
        if response.status_code == 200:
            print("✅ API está rodando")
            diag = response.json()
            print(f"   Modelo carregado: {diag.get('model_loaded', False)}")
        else:
            print(f"❌ API não responde: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Erro ao conectar na API: {e}")
        return

    # Testar upload na rota de teste
    print("\n🧪 Testando rota /system/test-upload...")
    try:
        with open(test_image, 'rb') as f:
            files = {'file': (test_image.name, f, 'image/jpeg')}
            data = {'id_token': 'admin_master_token'}
            response = requests.post(f"{base_url}/system/test-upload", files=files, data=data)

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload testado com sucesso!")
            print(f"   Arquivo: {result['file_info']['filename']}")
            print(f"   Tamanho: {result['file_info']['file_size']} bytes")
            print(f"   Validações: {result['file_info']['validation']}")
        else:
            print(f"❌ Erro no upload: {response.text}")

    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

    # Testar upload na rota real de detecção
    print("\n🎯 Testando rota /detection/analyze...")
    try:
        with open(test_image, 'rb') as f:
            files = {'file': (test_image.name, f, 'image/jpeg')}
            data = {'id_token': 'admin_master_token'}
            response = requests.post(f"{base_url}/detection/analyze", files=files, data=data)

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Detecção realizada com sucesso!")
            print(f"   Cadeiras detectadas: {result.get('detected_chairs', 0)}")
        else:
            print(f"❌ Erro na detecção: {response.text}")

    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

if __name__ == "__main__":
    test_upload_simulation()