import os
import sys
import asyncio
from pathlib import Path
from collections import defaultdict

# Adicionar raiz do projeto e api-tcc ao sys.path
api_tcc_dir = os.path.join(os.getcwd(), "api-tcc")
site_packages = os.path.join(api_tcc_dir, ".venv", "Lib", "site-packages")
if os.path.exists(site_packages):
    sys.path.insert(0, site_packages)
sys.path.insert(0, api_tcc_dir)

import cv2
from app.services.detection_service import DetectionService
detection_service = DetectionService()

async def test_video_realtime(video_path: Path, expected_detected: bool, sample_rate: int = 15):
    print(f"\n=========================================================================================")
    print(f"🎬 SIMULANDO TEMPO REAL: {video_path.name} (Esperado: {'EXTINTOR' if expected_detected else 'SEM EXTINTOR'})")
    print(f"=========================================================================================")
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Erro ao abrir vídeo: {video_path}")
        return False

    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    print(f"ℹ️ Total de quadros no vídeo: {total_video_frames} ({fps:.1f} FPS)")

    processed_frames = 0
    extinguisher_detected_frames = 0
    total_detections_by_class = defaultdict(int)
    reports_generated = 0
    sublayer_validations = 0

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % sample_rate != 0:
            continue

        processed_frames += 1

        # Chamar analyze_frame emulando a rota /detection/frame em tempo real
        res = await detection_service.analyze_frame(
            frame=frame,
            frame_index=frame_idx,
            model_name="extintor de incêndio",
            min_confidence=0.25,
            disable_compliance=False,
            imgsz=640
        )

        class_counts = res.get("class_counts", {})
        boxes = res.get("boxes", [])
        status = res.get("compliance_status")
        report = res.get("compliance_report")
        sub_analysis = res.get("sub_layer_analysis", [])

        has_extinguisher = any(
            any(k in c.lower() for k in ["extintor", "babcock", "walker", "yamato"])
            for c in class_counts.keys()
        )

        if has_extinguisher:
            extinguisher_detected_frames += 1

        if report:
            reports_generated += 1

        if sub_analysis:
            sublayer_validations += len(sub_analysis)

        for c, count in class_counts.items():
            total_detections_by_class[c] += count

        print(f"  Frame {frame_idx:03d}: Extintor={has_extinguisher} | Status={status} | Subcamada={len(sub_analysis)} | Classes={dict(class_counts)}")

    cap.release()

    extinguisher_ratio = (extinguisher_detected_frames / processed_frames) if processed_frames > 0 else 0
    print(f"\n📊 Resumo Simulação em Tempo Real:")
    print(f"   - Quadros analisados: {processed_frames}")
    print(f"   - Quadros com extintor: {extinguisher_detected_frames} ({extinguisher_ratio * 100:.1f}%)")
    print(f"   - Validações de sobcamada: {sublayer_validations}")
    print(f"   - Laudos gerados: {reports_generated}")
    print(f"   - Total por classe: {dict(total_detections_by_class)}")

    if expected_detected:
        passed = extinguisher_detected_frames > (processed_frames * 0.40)
    else:
        passed = extinguisher_detected_frames == 0

    print(f"   -> RESULTADO: {'✅ PASSOU' if passed else '❌ FALHOU'}")
    return passed

async def main():
    base_dir = Path(__file__).resolve().parent.parent
    pos_video = base_dir / "positivo.mp4"
    neg_video = base_dir / "negativo.mp4"

    print("⚡ Inicializando detecção para simulação em tempo real...")
    detection_service.preload_all_models()

    pos_ok = await test_video_realtime(pos_video, expected_detected=True, sample_rate=15)
    neg_ok = await test_video_realtime(neg_video, expected_detected=False, sample_rate=15)

    print("\n=========================================================================================")
    print("🏁 RESULTADO FINAL DA SIMULAÇÃO EM TEMPO REAL:")
    print(f"   Vídeo Positivo: {'✅ OK' if pos_ok else '❌ FALHOU'}")
    print(f"   Vídeo Negativo: {'✅ OK' if neg_ok else '❌ FALHOU'}")
    print("=========================================================================================")

    if not (pos_ok and neg_ok):
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
