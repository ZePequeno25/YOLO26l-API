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

VIDEO_TEST_CASES = [
    {
        "path": r"c:\Users\aborr\Projeto TCC\YOLO26l-API\positivo.mp4",
        "expected": True,
        "label": "Vídeo Positivo (Extintor na cena)"
    },
    {
        "path": r"c:\Users\aborr\Projeto TCC\YOLO26l-API\negativo.mp4",
        "expected": False,
        "label": "Vídeo Negativo (Sem extintor na cena)"
    }
]

async def run_video_tests():
    print("=" * 95)
    print("🎬 EXECUTANDO BATERIA DE TESTES DE PRECISÃO EM VÍDEOS (POSITIVO vs NEGATIVO)")
    print("=" * 95)
    
    detection_service.preload_all_models()
    
    results_summary = []
    
    for tc in VIDEO_TEST_CASES:
        filepath = tc["path"]
        if not os.path.exists(filepath):
            print(f"❌ Arquivo de vídeo não encontrado: {filepath}")
            continue
            
        filename = os.path.basename(filepath)
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"\n🎥 Testando: {tc['label']} ({filename} - {file_size_mb:.2f} MB)")
        print(f"   Esperado: {'EXTINTOR DETECTADO' if tc['expected'] else 'NENHUM EXTINTOR DETECTADO'}")
        
        with open(filepath, "rb") as f:
            content = f.read()
            
        upload_file = UploadFile(filename=filename, file=None)
        async def _read():
            return content
        upload_file.read = _read
        
        try:
            result = await detection_service.analyze(upload_file, model_name="extintor de incêndio")
            
            counts = result.get("class_counts", {})
            boxes = result.get("boxes", [])
            num_frames = result.get("num_frames_processed", 0)
            frames_with_det = result.get("frames_with_detections", 0)
            report = result.get("compliance_report")
            status = result.get("compliance_status")
            sub_layers = result.get("sub_layer_analysis", [])
            
            extintor_detected = any(c > 0 for k, c in counts.items() if any(ex in k.lower() for ex in ["extintor", "babcock", "walker", "yamato", "fire"]))
            
            passed = (extintor_detected == tc["expected"])
            
            print(f"   -> Quadros processados: {num_frames} | Quadros com detecção: {frames_with_det}")
            print(f"   -> Result counts: {counts}")
            print(f"   -> Detections (boxes): {len(boxes)}")
            for idx, b in enumerate(boxes[:10]):
                print(f"      • [{idx+1}] Frame {b.get('frame_index')}: '{b.get('class_name')}' conf={b.get('confidence'):.4f} (model={b.get('model_source')})")
            if len(boxes) > 10:
                print(f"      ... (+ {len(boxes)-10} mais caixas)")
            print(f"   -> Sub-layer analysis: {sub_layers}")
            print(f"   -> Compliance report: {report}")
            print(f"   -> TEST STATUS: {'✅ PASCOU' if passed else '❌ FALHOU'}")
            
            results_summary.append({
                "label": tc["label"],
                "expected": tc["expected"],
                "detected": extintor_detected,
                "passed": passed,
                "counts": counts,
                "frames": num_frames,
                "frames_with_det": frames_with_det
            })
            
        except Exception as e:
            print(f"   ❌ ERRO AO PROCESSAR VÍDEO: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                "label": tc["label"],
                "expected": tc["expected"],
                "detected": False,
                "passed": False,
                "error": str(e)
            })
            
    print("\n" + "=" * 95)
    print("📊 RESUMO DOS TESTES EM VÍDEOS")
    print("=" * 95)
    total_passed = sum(1 for r in results_summary if r.get("passed"))
    total_tests = len(results_summary)
    print(f"Resultado final: {total_passed}/{total_tests} vídeos passaram ({total_passed/total_tests*100:.1f}%)")
    for r in results_summary:
        st = "✅ OK" if r.get("passed") else "❌ FAIL"
        print(f"  [{st}] {r['label']}: Detectado={r.get('detected')}, Esperado={r.get('expected')} (Counts: {r.get('counts')})")
    print("=" * 95)

if __name__ == "__main__":
    asyncio.run(run_video_tests())
