#!/usr/bin/env python3
"""
Script para testar a API com arquivos analisados.
Testa o endpoint de análise e faz download do arquivo analisado.
"""

import requests
import json
from pathlib import Path
import sys

# Configuração
API_BASE_URL = "http://localhost:8000"
API_ANALYZE_ENDPOINT = "/detection/analyze-test"  # Endpoint de teste sem autenticação

def test_list_models():
    """Testa a listagem de modelos disponíveis."""
    print("📋 Testando listagem de modelos...")
    try:
        response = requests.get(f"{API_BASE_URL}/detection/models")
        data = response.json()
        print(f"✅ Modelos disponíveis: {data['models']}")
        print(f"   Modelo padrão: {data['default_model']}\n")
        return data['models']
    except Exception as e:
        print(f"❌ Erro ao listar modelos: {e}\n")
        return []

def test_analyze_image(image_path, model_name=None):
    """Testa a análise de uma imagem."""
    project_root = Path(__file__).parent.parent
    image_file = project_root / image_path

    if not image_file.exists():
        print(f"❌ Arquivo não encontrado: {image_file}")
        return

    print(f"🖼️  Testando análise de imagem: {image_file.name}")
    
    try:
        with open(image_file, "rb") as f:
            files = {"file": f}
            data = {}
            if model_name:
                data["model"] = model_name
            
            response = requests.post(
                f"{API_BASE_URL}{API_ANALYZE_ENDPOINT}",
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Análise concluída!")
            print(f"   Classes detectadas: {result['class_counts']}")
            print(f"   Frames processados: {result['num_frames_processed']}")
            print(f"   Cadeiras detectadas: {result['detected_chairs']}")
            
            if result.get('analyzed_file'):
                analyzed_file = Path(result['analyzed_file']).name
                print(f"   📁 Arquivo analisado: {analyzed_file}")
                
                # Fazer download do arquivo
                print(f"\n📥 Fazendo download do arquivo analisado...")
                download_response = requests.get(
                    f"{API_BASE_URL}/detection/download/{analyzed_file}"
                )
                
                if download_response.status_code == 200:
                    download_path = project_root / "downloaded_outputs" / analyzed_file
                    download_path.parent.mkdir(exist_ok=True)
                    with open(download_path, "wb") as f:
                        f.write(download_response.content)
                    print(f"✅ Arquivo baixado: {download_path}")
                else:
                    print(f"❌ Erro ao baixar arquivo: {download_response.status_code}")
            
            print()
        else:
            print(f"❌ Erro na análise: {response.status_code}")
            print(f"   {response.text}\n")
    except Exception as e:
        print(f"❌ Erro: {e}\n")

def test_analyze_video(video_path, model_name=None):
    """Testa a análise de um vídeo."""
    project_root = Path(__file__).parent.parent
    video_file = project_root / video_path

    if not video_file.exists():
        print(f"❌ Arquivo não encontrado: {video_file}")
        return

    print(f"🎬 Testando análise de vídeo: {video_file.name}")
    
    try:
        with open(video_file, "rb") as f:
            files = {"file": f}
            data = {}
            if model_name:
                data["model"] = model_name
            
            response = requests.post(
                f"{API_BASE_URL}{API_ANALYZE_ENDPOINT}",
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Análise concluída!")
            print(f"   Classes detectadas: {result['class_counts']}")
            print(f"   Frames processados: {result['num_frames_processed']}")
            print(f"   Frames com detecção: {result.get('frames_with_detections', 'N/A')}")
            
            if result.get('analyzed_file'):
                analyzed_file = Path(result['analyzed_file']).name
                print(f"   📁 Arquivo analisado: {analyzed_file}")
                
                # Fazer download do arquivo
                print(f"\n📥 Fazendo download do vídeo analisado...")
                download_response = requests.get(
                    f"{API_BASE_URL}/detection/download/{analyzed_file}"
                )
                
                if download_response.status_code == 200:
                    download_path = project_root / "downloaded_outputs" / analyzed_file
                    download_path.parent.mkdir(exist_ok=True)
                    with open(download_path, "wb") as f:
                        f.write(download_response.content)
                    print(f"✅ Vídeo baixado: {download_path}")
                else:
                    print(f"❌ Erro ao baixar vídeo: {download_response.status_code}")
            
            print()
        else:
            print(f"❌ Erro na análise: {response.status_code}")
            print(f"   {response.text}\n")
    except Exception as e:
        print(f"❌ Erro: {e}\n")

def main():
    print("🚀 Testando API de Detecção com Arquivos Analisados\n")
    
    # Testar listagem de modelos
    models = test_list_models()
    
    # Testar com imagem
    test_analyze_image(
        "data/content/custom_data/test/images/110_png_jpg.rf.18b130280ec44c73e4452afecfc09ea9.jpg",
        model_name="chair"
    )
    
    print("✅ Testes concluídos!")

if __name__ == "__main__":
    main()