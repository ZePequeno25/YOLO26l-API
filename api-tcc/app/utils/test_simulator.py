"""
Module to simulate video input from a static image for load testing.
"""
import logging
import os
from uuid import uuid4

import cv2

logger = logging.getLogger(__name__)

# --- TOGGLE DO TESTE DE CARGA ---
# Mude para False para desativar a conversão de imagem para vídeo de 20 frames
ATIVAR_TESTE_CARGA = False


def simulate_video_from_image(image_path: str) -> str:
    """
    Se ATIVAR_TESTE_CARGA for True, lê a imagem, clona 20 vezes num vídeo mp4,
    apaga a imagem original e devolve o novo caminho do vídeo.
    Caso contrário, devolve None.
    """
    if not ATIVAR_TESTE_CARGA:
        return None

    logger.info(
        "🧪 TESTE ATIVO: Convertendo imagem num vídeo de 20 frames "
        "para simulação de carga..."
    )
    img = cv2.imread(image_path)
    if img is None:
        return None

    test_video_path = f"temp_test_{uuid4().hex}.mp4"
    h, w = img.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    # Acelera ligeiramente a FPS para o vídeo não ser excessivamente lento (ex: 5 fps)
    out = cv2.VideoWriter(test_video_path, fourcc, 5.0, (w, h))

    for _ in range(20):
        out.write(img)
    out.release()

    # Apagar a imagem original
    try:
        if os.path.exists(image_path):
            os.unlink(image_path)
    except OSError as e:
        logger.warning(
            "Não foi possível apagar imagem original durante simulação: %s",
            e
        )

    return test_video_path
