import os
import sys
import asyncio
from pathlib import Path

api_tcc_dir = os.path.join(os.getcwd(), "api-tcc")
site_packages = os.path.join(api_tcc_dir, ".venv", "Lib", "site-packages")
if os.path.exists(site_packages):
    sys.path.insert(0, site_packages)
sys.path.insert(0, api_tcc_dir)

import cv2
from app.services.detection_service import DetectionService
from app.services.sublayer_service import sub_layer_manager

detection_service = DetectionService()

async def test_roi():
    cap = cv2.VideoCapture("positivo.mp4")
    cap.set(cv2.CAP_PROP_POS_FRAMES, 270)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("Erro ao ler frame 270")
        return

    res_p1 = detection_service._run_single_model_inference("extintor_co2_silica", frame, False, 0.40)
    boxes = detection_service._extract_raw_boxes_from_results(res_p1, "extintor_co2_silica")
    print(f"Boxes no frame 270: {boxes}")

    h, w = frame.shape[:2]
    for b in boxes:
        x1, y1, x2, y2 = b["x1_raw"], b["y1_raw"], b["x2_raw"], b["y2_raw"]
        roi = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        print(f"ROI shape: {roi.shape}")
        
        # Testar diretamente o submodelo na ROI
        sub_dets = sub_layer_manager._run_sub_model_inference(roi, "submodelo_extintor_componentes")
        print(f"Sub-dets diretos do submodelo na ROI: {sub_dets}")

        # Testar inspect_cropped_roi
        res = sub_layer_manager.inspect_cropped_roi(b["class_name"], roi, context_boxes=[])
        print(f"Inspect cropped ROI: {res}")

if __name__ == "__main__":
    asyncio.run(test_roi())
