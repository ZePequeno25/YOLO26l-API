#!/usr/bin/env python3
"""
Teste com imagem sem objetos para verificar tratamento de erro
"""
import requests
import cv2
import numpy as np
import tempfile
import os
from pathlib import Path

def test_empty_detection():
    """Testa detecção em imagem vazia (sem objetos)"""
    print("🧪 TESTE DE DETECÇÃO - IMAGEM SEM OBJETOS\n")

    base_url = "http://localhost:8000"
    
    # Criar imagem vazia (branca)
    empty_img = np.ones((640, 640, 3), dtype=np.uint8) * 255
    
    # Salvar temporariamente
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
        cv2.imwrite(tmp_path, empty_img)
    
    try:
        print(f"📁 Imagem de teste: {os.path.getsize(tmp_path)} bytes (vazia)\n")
        
        # Testar detecção
        with open(tmp_path, 'rb') as f:
            files = {'file': (os.path.basename(tmp_path), f, 'image/jpeg')}
            data = {'id_token': 'admin_master_token'}
            
            response = requests.post(
                f"{base_url}/detection/analyze",
                files=files,
                data=data,
                timeout=60
            )
        
        print(f"Status: {response.status_code}\n")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Detecção funcionou (sem erros)!")
            print(f"   Cadeiras detectadas: {result.get('detected_chairs', 0)}")
            print(f"   Frames processados: {result.get('num_frames_processed', 0)}")
            print(f"   Frames com detecção: {result.get('frames_with_detections', 0)}")
            print(f"   Mensagem: {result.get('message', 'N/A')}")
            print(f"   Objetos: {result.get('class_counts', {})}")
        else:
            print(f"❌ Erro: {response.status_code}")
            print(response.json() if response.headers.get('content-type') == 'application/json' else response.text)
    
    finally:
        # Limpar
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    test_empty_detection()
