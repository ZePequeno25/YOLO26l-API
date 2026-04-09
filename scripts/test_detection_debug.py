#!/usr/bin/env python3
"""
Script de diagnóstico para testar o serviço de detecção localmente
"""
import os
import sys
import tempfile
import logging
from pathlib import Path

# Adicionar pasta do projeto ao path
sys.path.insert(0, r"C:\\Users\\aborr\\Projeto TCC\\api-tcc")

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from config.settings import settings
from ultralytics import YOLO
import cv2
import numpy as np

def test_model_loading():
    """Teste 1: Verificar se o modelo carrega"""
    print("\n" + "="*60)
    print("TESTE 1: Carregando modelo YOLO + OpenVINO")
    print("="*60)
    
    model_path = settings.MODEL_PATH
    print(f"Caminho do modelo: {model_path}")
    print(f"Modelo existe: {os.path.exists(model_path)}")
    
    if os.path.exists(model_path):
        print(f"Arquivos no diretório: {os.listdir(model_path)}")
    
    try:
        model = YOLO(model_path)
        print(f"✅ Modelo carregado com sucesso!")
        print(f"   Classes: {len(model.names)}")
        print(f"   Nomes: {list(model.names.values())}")
        return model
    except Exception as e:
        print(f"❌ Erro ao carregar modelo: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_inference_on_synthetic_image(model):
    """Teste 2: Testar inferência com uma imagem sintética"""
    print("\n" + "="*60)
    print("TESTE 2: Inferência com imagem sintética")
    print("="*60)
    
    if model is None:
        print("❌ Modelo não carregado, pulando teste")
        return
    
    try:
        # Criar imagem sintética (branca com alguns pixels aleatórios)
        img = np.ones((640, 640, 3), dtype=np.uint8) * 255
        np.random.seed(42)
        for _ in range(100):
            x, y = np.random.randint(100, 540, 2)
            cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
        
        # Salvar em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            cv2.imwrite(tmp_path, img)
        
        print(f"Imagem sintética criada: {tmp_path}")
        print(f"Arquivo existe: {os.path.exists(tmp_path)}")
        print(f"Tamanho do arquivo: {os.path.getsize(tmp_path)} bytes")
        
        # Testar leitura com OpenCV
        test_img = cv2.imread(tmp_path)
        if test_img is None:
            print("❌ Erro: OpenCV não consegue ler a imagem criada!")
            return
        print(f"✅ OpenCV consegue ler a imagem: {test_img.shape}")
        
        # Testar com YOLO
        print(f"\nExecutando detecção...")
        results = model.track(
            source=tmp_path,
            device="intel:gpu",
            verbose=True,
            persist=True
        )
        
        print(f"✅ Inferência concluída!")
        print(f"   Resultados retornados: {len(results)}")
        for i, result in enumerate(results):
            print(f"   Frame {i}: {len(result.boxes)} detecções")
        
        os.unlink(tmp_path)
        
    except Exception as e:
        print(f"❌ Erro na inferência: {e}")
        import traceback
        traceback.print_exc()

def test_with_real_image():
    """Teste 3: Testar com uma imagem real se disponível"""
    print("\n" + "="*60)
    print("TESTE 3: Inferência com possível imagem real")
    print("="*60)
    
    # Procurar por imagens no diretório
    test_dirs = [
        r"C:\Users\aborr\Projeto TCC\content\custom_data\train",
        r"C:\Users\aborr\Projeto TCC\video cadeiras"
    ]
    
    test_image = None
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.lower().endswith((".jpg", ".jpeg", ".png")):
                    test_image = os.path.join(test_dir, file)
                    break
            if test_image:
                break
    
    if test_image:
        print(f"Imagem encontrada: {test_image}")
        print(f"Existe: {os.path.exists(test_image)}")
        
        # Testar leitura
        img = cv2.imread(test_image)
        if img is None:
            print(f"❌ Erro ao ler imagem com OpenCV")
        else:
            print(f"✅ Imagem lida: {img.shape}")
    else:
        print("ℹ️  Nenhuma imagem real encontrada para teste")

if __name__ == "__main__":
    print("\n🔍 DIAGNÓSTICO DO SERVIÇO DE DETECÇÃO\n")
    
    model = test_model_loading()
    test_inference_on_synthetic_image(model)
    test_with_real_image()
    
    print("\n" + "="*60)
    print("DIAGNÓSTICO CONCLUÍDO")
    print("="*60 + "\n")
