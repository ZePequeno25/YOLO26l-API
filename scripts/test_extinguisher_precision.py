import os
import sys
import asyncio

# Ensure api-tcc and its venv site-packages are in sys.path
api_tcc_dir = os.path.join(os.getcwd(), "api-tcc")
site_packages = os.path.join(api_tcc_dir, ".venv", "Lib", "site-packages")
if os.path.exists(site_packages):
    sys.path.insert(0, site_packages)
sys.path.insert(0, api_tcc_dir)

from app.services.detection_service import DetectionService
from fastapi import UploadFile

detection_service = DetectionService()

USER_UPLOADED_DIR = r"C:\Users\aborr\.gemini\antigravity-ide\brain\40e32042-1838-4728-9fde-0a4bc9466e0d\.user_uploaded"

TEST_CASES = [
    {"file": "media_1791603258749.png", "expected": True, "label": "Positivo 1 - Extintor Pó BC (close up)"},
    {"file": "media_1791603266706.png", "expected": True, "label": "Positivo 2 - Extintor Pó ABC + Placa"},
    {"file": "media_1791603273606.png", "expected": True, "label": "Positivo 3 - Extintor Resil (corpo inteiro)"},
    {"file": "media_1791603386704.png", "expected": False, "label": "Negativo 1 - Sala de estar (sem extintor)"},
    {"file": "media_1791603395867.png", "expected": False, "label": "Negativo 2 - Quadro/Poltrona (sem extintor)"},
]

async def run_tests():
    print("=" * 90)
    print("🧪 EXECUTANDO BATERIA DE TESTES DE PRECISÃO PARA DETECÇÃO DE EXTINTOR DE INCÊNDIO")
    print("=" * 90)
    
    # Warmup models
    detection_service.preload_all_models()
    
    results_summary = []
    
    for tc in TEST_CASES:
        filepath = os.path.join(USER_UPLOADED_DIR, tc["file"])
        if not os.path.exists(filepath):
            print(f"❌ Arquivo não encontrado: {filepath}")
            continue
            
        print(f"\n📸 Testando: {tc['label']} ({tc['file']})")
        print(f"   Esperado: {'EXTINTOR DETECTADO' if tc['expected'] else 'NENHUM EXTINTOR DETECTADO'}")
        
        with open(filepath, "rb") as f:
            content = f.read()
            
        upload_file = UploadFile(filename=tc["file"], file=None)
        # Mocking read method
        async def _read():
            return content
        upload_file.read = _read
        
        try:
            # Let's inspect raw boxes from internal model inference to see confidences
            results = detection_service._run_single_model_inference("extintor_co2_silica", filepath, is_video=False)
            raw_boxes = results[0].boxes if results else []
            print(f"   [RAW MODEL INFERENCE] Found {len(raw_boxes)} raw bounding boxes:")
            for b in raw_boxes:
                cls_id = int(b.cls[0].item())
                cname = results[0].names.get(cls_id, str(cls_id))
                conf = float(b.conf[0].item())
                print(f"      • Raw box: '{cname}' | conf={conf:.4f} ({conf*100:.1f}%)")

            result = await detection_service.analyze(upload_file, model_name="extintor de incêndio")
            
            counts = result.get("class_counts", {})
            boxes = result.get("boxes", [])
            report = result.get("compliance_report")
            status = result.get("compliance_status")
            sub_layers = result.get("sub_layer_analysis", [])
            
            extintor_detected = any(c > 0 for k, c in counts.items() if "extintor" in k.lower() or "fire" in k.lower())
            
            passed = (extintor_detected == tc["expected"])
            
            print(f"   -> Result counts: {counts}")
            print(f"   -> Detections (boxes): {len(boxes)}")
            for b in boxes:
                print(f"      • {b.get('class_name')}: conf={b.get('confidence'):.4f} (model={b.get('model_source')})")
            print(f"   -> Sub-layer analysis: {sub_layers}")
            print(f"   -> Compliance report: {report}")
            print(f"   -> TEST STATUS: {'✅ PASCOU' if passed else '❌ FALHOU'}")
            
            results_summary.append({
                "label": tc["label"],
                "expected": tc["expected"],
                "detected": extintor_detected,
                "passed": passed,
                "counts": counts,
                "boxes_count": len(boxes)
            })
            
        except Exception as e:
            print(f"   ❌ ERRO AO PROCESSAR: {e}")
            results_summary.append({
                "label": tc["label"],
                "expected": tc["expected"],
                "detected": False,
                "passed": False,
                "error": str(e)
            })
            
    print("\n" + "=" * 90)
    print("📊 RESUMO DOS TESTES DE PRECISÃO")
    print("=" * 90)
    total_passed = sum(1 for r in results_summary if r.get("passed"))
    total_tests = len(results_summary)
    print(f"Resultado final: {total_passed}/{total_tests} testes passaram ({total_passed/total_tests*100:.1f}%)")
    for r in results_summary:
        st = "✅ OK" if r.get("passed") else "❌ FAIL"
        print(f"  [{st}] {r['label']}: Detectado={r.get('detected')}, Esperado={r.get('expected')}")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(run_tests())
