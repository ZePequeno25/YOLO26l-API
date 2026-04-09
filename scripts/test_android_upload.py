#!/usr/bin/env python3
"""
Script para simular upload do Android e debugar formatos
"""
import requests
import os
from pathlib import Path
import json

def test_android_upload():
    """Testa upload como Android faria"""
    print("📱 TESTE DE UPLOAD (Simulando Android)\n")

    base_url = "http://localhost:8000"
    
    # Procurar uma imagem
    test_images = list(Path("content/custom_data/train/images").glob("*.jpg"))
    if not test_images:
        print("❌ Nenhuma imagem encontrada")
        return
    
    test_image = test_images[0]
    print(f"📁 Usando: {test_image}\n")
    
    # === TESTE 1: Debug bruto ===
    print("=" * 60)
    print("TESTE 1: Rota /debug-upload (dump bruto)")
    print("=" * 60)
    
    try:
        with open(test_image, 'rb') as f:
            files = {'file': (test_image.name, f, 'image/jpeg')}
            data = {'id_token': 'admin_master_token'}
            
            response = requests.post(
                f"{base_url}/system/debug-upload",
                files=files,
                data=data,
                timeout=10
            )
        
        if response.status_code == 200:
            debug = response.json()
            
            print("\n✅ Arquivo recebido:")
            print(f"   Nome: {debug['data']['filename']}")
            print(f"   Tamanho: {debug['data']['file_size_mb']:.2f} MB ({debug['data']['file_size_bytes']} bytes)")
            print(f"   Content-Type: {debug['data']['content_type']}")
            print(f"   Extension: {debug['data'].get('extension', 'N/A')}")
            print(f"   Tipo detectado: {debug['data'].get('detected_file_type', 'Desconhecido')}")
            print(f"\n   Magic bytes (hex): {debug['data']['magic_bytes_hex'][:32]}...")
            print(f"   Primeiros 200 bytes (hex):\n   {debug['data']['first_200_bytes_hex'][:200]}")
            
        else:
            print(f"❌ Erro: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # === TESTE 2: Test-upload ===
    print("\n" + "=" * 60)
    print("TESTE 2: Rota /test-upload (validação)")
    print("=" * 60)
    
    try:
        with open(test_image, 'rb') as f:
            files = {'file': (test_image.name, f, 'image/jpeg')}
            data = {'id_token': 'admin_master_token'}
            
            response = requests.post(
                f"{base_url}/system/test-upload",
                files=files,
                data=data,
                timeout=10
            )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Validação OpenCV e PIL:")
            print(f"   {json.dumps(result['file_info'].get('validation', {}), indent=4)}")
        else:
            print(f"❌ Erro: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # === TESTE 3: Detecção real ===
    print("\n" + "=" * 60)
    print("TESTE 3: Rota /detection/analyze (detecção real)")
    print("=" * 60)
    
    try:
        with open(test_image, 'rb') as f:
            files = {'file': (test_image.name, f, 'image/jpeg')}
            data = {'id_token': 'admin_master_token'}
            
            response = requests.post(
                f"{base_url}/detection/analyze",
                files=files,
                data=data,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Detecção realizada:")
            print(f"   Cadeiras: {result.get('detected_chairs', 0)}")
            print(f"   Frames processados: {result.get('num_frames_processed', 0)}")
            print(f"   Detecções: {result.get('class_counts', {})}")
        else:
            print(f"❌ Erro: {response.status_code}")
            print(response.json() if response.headers.get('content-type') == 'application/json' else response.text)
    
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    test_android_upload()
