#!/usr/bin/env python3
"""
Test detection com logging detalhado para ver exatamente o que está sendo retornado
"""
import sys
sys.path.insert(0, r"C:\Users\aborr\Projeto TCC\api-tcc")

import asyncio
from app.services.detection_service import DetectionService
from fastapi import UploadFile
import io
from pathlib import Path

async def test_detection():
    # Usar uma imagem que tem cadeiras
    image_path = Path(r"C:\Users\aborr\Projeto TCC\content\custom_data\train\images\100_png_jpg.rf.3207306b5cac7c3702180db1784da211.jpg")
    
    if not image_path.exists():
        print(f"❌ Imagem não encontrada: {image_path}")
        return
    
    print(f"📸 Testando com imagem: {image_path.name}")
    
    # Ler o arquivo
    with open(image_path, "rb") as f:
        content = f.read()
    
    # Criar um arquivo simulado do FastAPI
    uploaded_file = UploadFile(
        file=io.BytesIO(content),
        filename="test.jpg"
    )
    
    # Executar detecção
    service = DetectionService()
    
    print("\n🔍 Executando análise...")
    result = await service.analyze(uploaded_file)
    
    print("\n✅ RESULTADO DA DETECÇÃO:")
    print(f"  class_counts: {result['class_counts']}")
    print(f"  detected_chairs: {result['detected_chairs']}")
    print(f"  num_frames_processed: {result['num_frames_processed']}")
    print(f"  frames_with_detections: {result['frames_with_detections']}")
    print(f"  message: {result['message']}")
    
    print("\n📊 Análise:")
    if "0" in result['class_counts']:
        print("  ⚠️ PROBLEMA ENCONTRADO! Class '0' (string) está no resultado")
        print(f"      Valor: {result['class_counts']['0']}")
    
    if "chair" in result['class_counts']:
        print("  ✅ Class 'chair' detectada corretamente")
    else:
        print(f"  ⚠️ Class 'chair' NÃO encontrada. Classes presentes: {list(result['class_counts'].keys())}")

# Executar
asyncio.run(test_detection())
