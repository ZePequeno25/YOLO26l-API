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

detection_service = DetectionService()

async def debug_frames():
    cap = cv2.VideoCapture("positivo.mp4")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    print(f"Total quadros em positivo.mp4: {total_frames}")

    # Checar alguns quadros onde falhou (ex: frame 60, frame 120, frame 150) e onde passou (frame 270)
    test_indices = [30, 60, 90, 120, 150, 180, 210, 240, 270]

    for target_idx in test_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
        ret, frame = cap.read()
        if not ret:
            continue

        target_imgsz = 640
        resized_p1 = cv2.resize(frame, (target_imgsz, target_imgsz))
        resized_p2 = cv2.flip(resized_p1, 1)

        # Inferência pura P1
        res_p1 = detection_service._run_single_model_inference("extintor_co2_silica", resized_p1, False, 0.20, target_imgsz)
        boxes_p1 = detection_service._extract_raw_boxes_from_results(res_p1, "extintor_co2_silica")

        # Inferência pura P2
        res_p2 = detection_service._run_single_model_inference("extintor_co2_silica", resized_p2, False, 0.20, target_imgsz)
        boxes_p2 = detection_service._extract_raw_boxes_from_results(res_p2, "extintor_co2_silica")

        p1_strs = [f"{b['class_name']}: {b['confidence']:.2f}" for b in boxes_p1]
        p2_strs = [f"{b['class_name']}: {b['confidence']:.2f}" for b in boxes_p2]
        print(f"\n--- Frame {target_idx} ---")
        print(f"  P1 (Original): {p1_strs}")
        print(f"  P2 (Flipped) : {p2_strs}")

    cap.release()

if __name__ == "__main__":
    asyncio.run(debug_frames())
