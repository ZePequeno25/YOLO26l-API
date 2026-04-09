#!/usr/bin/env python3
"""
Script para testar dispositivos disponíveis para YOLO
"""
import torch
from ultralytics import YOLO
import sys
import os

def test_devices():
    """Testa diferentes dispositivos disponíveis"""
    print("🔍 TESTE DE DISPOSITIVOS DISPONÍVEIS\n")

    # Verificar PyTorch
    print(f"PyTorch versão: {torch.__version__}")
    print(f"CUDA disponível: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA versão: {torch.version.cuda}")
        print(f"GPUs CUDA: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")

    # Testar diferentes dispositivos YOLO
    devices_to_test = ["cpu", "cuda", "cuda:0", "0", "gpu"]
    model_path = "my_model-85%/my_model.pt"

    if not os.path.exists(model_path):
        print(f"❌ Modelo não encontrado: {model_path}")
        return

    print(f"\n📁 Testando modelo: {model_path}")

    for device in devices_to_test:
        try:
            print(f"\n🧪 Testando dispositivo: '{device}'")
            model = YOLO(model_path)
            # Tentar uma inferência simples
            results = model("content/custom_data/train/images/100_png_jpg.rf.3207306b5cac7c3702180db1784da211.jpg",
                          device=device, verbose=False, max_det=1)
            print(f"   ✅ Sucesso! Dispositivo '{device}' funciona")
            print(f"   Detecções: {len(results[0].boxes)}")
            break
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")

    # Testar dispositivos OpenVINO específicos
    print("\n🔧 Testando dispositivos OpenVINO:")
    ov_devices = ["CPU", "GPU", "AUTO"]
    for device in ov_devices:
        try:
            print(f"🧪 Testando OpenVINO: '{device}'")
            model = YOLO(model_path)
            results = model("content/custom_data/train/images/100_png_jpg.rf.3207306b5cac7c3702180db1784da211.jpg",
                          device=device, verbose=False, max_det=1)
            print(f"   ✅ OpenVINO '{device}' funciona!")
            print(f"   Detecções: {len(results[0].boxes)}")
        except Exception as e:
            print(f"   ❌ OpenVINO '{device}': {str(e)}")

if __name__ == "__main__":
    test_devices()