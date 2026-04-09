#!/usr/bin/env python3
"""
Script para testar leitura de imagens com diferentes bibliotecas
"""
import cv2
import numpy as np
import os
from pathlib import Path

def test_image_reading():
    """Testa leitura de imagem com OpenCV e PIL"""
    print("🔍 TESTE DE LEITURA DE IMAGEM\n")

    # Procurar por imagens no projeto
    search_paths = [
        Path("content/custom_data/train"),
        Path("content/custom_data/valid"),
        Path("content/custom_data/test"),
        Path("video cadeiras")
    ]

    test_images = []
    for search_path in search_paths:
        if search_path.exists():
            for file in search_path.rglob("*"):
                if file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    test_images.append(file)
                    if len(test_images) >= 3:  # Pegar apenas 3 imagens para teste
                        break
            if len(test_images) >= 3:
                break

    if not test_images:
        print("❌ Nenhuma imagem encontrada para teste")
        return

    print(f"📁 Encontradas {len(test_images)} imagens para teste\n")

    for i, img_path in enumerate(test_images, 1):
        print(f"🖼️  Teste {i}: {img_path}")
        print(f"   Tamanho: {os.path.getsize(img_path)} bytes")

        # Teste com OpenCV
        try:
            img_cv = cv2.imread(str(img_path))
            if img_cv is None:
                print("   ❌ OpenCV: falhou ao ler")
            else:
                print(f"   ✅ OpenCV: {img_cv.shape}, dtype: {img_cv.dtype}")
        except Exception as e:
            print(f"   ❌ OpenCV erro: {e}")

        # Teste com PIL
        try:
            from PIL import Image
            img_pil = Image.open(img_path)
            img_pil.verify()
            print(f"   ✅ PIL: {img_pil.format}, {img_pil.size}, mode: {img_pil.mode}")
            img_pil.close()
        except Exception as e:
            print(f"   ❌ PIL erro: {e}")

        print()

def create_test_image():
    """Cria uma imagem de teste simples"""
    print("🎨 CRIANDO IMAGEM DE TESTE\n")

    # Criar imagem simples: quadrado branco com círculo vermelho
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    cv2.circle(img, (100, 100), 50, (0, 0, 255), -1)  # Círculo vermelho

    test_path = Path("test_image.jpg")
    success = cv2.imwrite(str(test_path), img)

    if success:
        print(f"✅ Imagem de teste criada: {test_path}")
        print(f"   Tamanho: {os.path.getsize(test_path)} bytes")

        # Testar leitura da imagem criada
        img_read = cv2.imread(str(test_path))
        if img_read is not None:
            print(f"   ✅ Leitura OK: {img_read.shape}")
        else:
            print("   ❌ Falha ao ler imagem criada")

        # Limpar
        os.remove(test_path)
        print("   🗑️  Arquivo de teste removido")
    else:
        print("❌ Falha ao criar imagem de teste")

if __name__ == "__main__":
    test_image_reading()
    print("\n" + "="*50 + "\n")
    create_test_image()