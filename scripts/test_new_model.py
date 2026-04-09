#!/usr/bin/env python3
"""
Script para testar o novo modelo de detecção de cadeiras.
Este script carrega o modelo, processa uma imagem de teste e mostra os resultados.
"""

import sys
import os
from pathlib import Path
from ultralytics import YOLO
import cv2

def main():
    # Caminhos
    project_root = Path(__file__).parent.parent
    model_path = project_root / "models" / "my_model" / "my_model.pt"
    test_image_path = project_root / "data" / "content" / "custom_data" / "test" / "images"  # Ajuste conforme necessário

    # Verificar se o modelo existe
    if not model_path.exists():
        print(f"Erro: Modelo não encontrado em {model_path}")
        sys.exit(1)

    # Carregar o modelo
    print(f"Carregando modelo: {model_path}")
    model = YOLO(str(model_path))

    # Mostrar informações do modelo
    print("Informações do modelo:")
    print(f"  Classes: {model.names}")
    print(f"  Número de classes: {len(model.names)}")

    # Procurar uma imagem de teste
    test_images = list(test_image_path.glob("*.jpg")) + list(test_image_path.glob("*.png"))
    if not test_images:
        print(f"Nenhuma imagem de teste encontrada em {test_image_path}")
        print("Adicione imagens de teste na pasta data/content/custom_data/test/images/")
        sys.exit(1)

    test_image = test_images[0]  # Usar a primeira imagem encontrada
    print(f"Testando com imagem: {test_image}")

    # Fazer inferência
    results = model(str(test_image))

    # Processar resultados
    detections = []
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                cls = int(box.cls.item())
                conf = box.conf.item()
                class_name = model.names.get(cls, f"Classe {cls}")
                detections.append({
                    "classe": class_name,
                    "confiança": conf,
                    "coordenadas": box.xyxy.tolist()
                })

    # Mostrar resultados
    print(f"\nResultados da detecção ({len(detections)} objetos encontrados):")
    for i, det in enumerate(detections, 1):
        print(f"  {i}. {det['classe']} - Confiança: {det['confiança']:.2%}")

    # Salvar imagem com detecções (opcional)
    if detections:
        img = cv2.imread(str(test_image))
        for det in detections:
            x1, y1, x2, y2 = det['coordenadas'][0]
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(img, f"{det['classe']} {det['confiança']:.2f}",
                       (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        output_path = project_root / "scripts" / "test_result.jpg"
        cv2.imwrite(str(output_path), img)
        print(f"\nImagem com detecções salva em: {output_path}")

    print("\nTeste concluído!")

if __name__ == "__main__":
    main()