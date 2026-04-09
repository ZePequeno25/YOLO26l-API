from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from config.settings import settings
from app.services.detection_service import DetectionService
from app.core.firebase import verify_id_token
import os
import cv2
import logging
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["Sistema"])

@router.get("/status")
async def get_status():
    return {
        "status": "online",
        "model": "YOLO + OpenVINO (Intel Arc)",
        "host": settings.HOST,
        "port": settings.PORT
    }

@router.get("/classes")
async def get_classes():
    service = DetectionService()
    return {
        "detectable_classes": list(service.model.names.values()),
        "total": len(service.model.names)
    }

@router.get("/diagnostic")
async def get_diagnostic():
    """Rota de diagnóstico para verificar configuração e modelo"""
    diagnostics = {
        "model_path": settings.MODEL_PATH,
        "model_path_exists": os.path.exists(settings.MODEL_PATH),
        "inference_device": settings.INFERENCE_DEVICE,
    }
    
    try:
        # Verificar arquivos do modelo
        if os.path.exists(settings.MODEL_PATH):
            files = os.listdir(settings.MODEL_PATH)
            diagnostics["model_files"] = files
        
        # Tentar carregar o modelo
        service = DetectionService()
        diagnostics["model_loaded"] = True
        diagnostics["model_classes"] = len(service.model.names)
        diagnostics["class_names"] = list(service.model.names.values())
    except Exception as e:
        diagnostics["model_loaded"] = False
        diagnostics["model_error"] = str(e)
    
    return diagnostics

@router.post("/debug-upload")
async def debug_upload_raw(
    file: UploadFile = File(...),
    id_token: str = Form(...)
):
    """
    Rota de debug para ver EXATAMENTE como o cliente está enviando o arquivo.
    Sem validações - apenas mostra o que foi recebido.
    """
    try:
        verify_id_token(id_token)
        
        # Ler conteúdo sem nenhuma validação
        content = await file.read()
        
        debug_info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "content_type_header": file.content_type,
            "file_size_bytes": len(content),
            "file_size_mb": len(content) / (1024 * 1024),
        }
        
        # Extension do arquivo
        if file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            debug_info["extension"] = ext
        
        # Magic bytes (primeiros 32 bytes em hex)
        if len(content) > 0:
            debug_info["magic_bytes_hex"] = content[:32].hex()
            
            # Tentar interpretar os magic bytes
            magic = content[:4]
            signatures = {
                b'\xFF\xD8\xFF\xE0': "JPEG (JFIF)",
                b'\xFF\xD8\xFF\xE1': "JPEG (EXIF)",
                b'\xFF\xD8\xFF\xE2': "JPEG",
                b'\x89PNG': "PNG",
                b'GIF8': "GIF",
                b'RIFF': "AVI/WAV/WebP",
                b'\x00\x00\x00\x18ftyp': "MP4/MOV",
                b'\x1A\x45\xDF\xA3': "MKV",
            }
            
            detected = "Desconhecido"
            for sig, desc in signatures.items():
                if magic.startswith(sig[:len(magic)]):
                    detected = desc
                    break
            
            debug_info["detected_file_type"] = detected
        
        # Headers adicionais
        debug_info["headers"] = {
            "content-type": file.content_type,
            "filename": file.filename,
        }
        
        # Tamanho dos primeiros 200 bytes para análise
        debug_info["first_200_bytes_hex"] = content[:200].hex()
        
        return {
            "status": "debug_info_captured",
            "warning": "Este é um dump bruto do que foi recebido. Use para diagnosticar problemas de upload.",
            "data": debug_info
        }
        
    except Exception as e:
        logger.error(f"Erro no debug: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-upload")
async def test_upload(
    file: UploadFile = File(...),
    id_token: str = Form(...)
):
    """Rota de teste para validar upload de arquivos sem fazer detecção"""
    try:
        # Verificar autenticação
        verify_id_token(id_token)
        
        # Informações básicas do arquivo
        file_info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size": 0,
            "validation": {}
        }
        
        # Ler conteúdo
        content = await file.read()
        file_info["file_size"] = len(content)
        
        if file_info["file_size"] == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio")
        
        # Determinar extensão
        suffix = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        file_info["extension"] = suffix
        
        # Validação básica
        if suffix in [".jpg", ".jpeg", ".png"]:
            file_info["validation"]["format"] = "Imagem OK"
        elif suffix in [".mp4", ".mov", ".avi", ".mkv"]:
            file_info["validation"]["format"] = "Vídeo OK"
        else:
            file_info["validation"]["format"] = f"Formato desconhecido: {suffix}"
        
        return {
            "success": True,
            "message": "Upload testado com sucesso",
            "file_info": file_info
        }
        
    except Exception as e:
        logger.error(f"Erro no teste de upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detection-debug")
async def detection_debug(
    file: UploadFile = File(...),
    id_token: str = Form(...)
):
    """
    Endpoint de debug para análise detalhada mostrando TODAS as classes detectadas
    com contagens e mapeamento de índices. Útil para diagnosticar problemas.
    """
    try:
        verify_id_token(id_token)
        
        service = DetectionService()
        result = await service.analyze(file)
        
        # Informações detalhadas
        model_info = {
            "total_classes_in_model": len(service.model.names),
            "all_class_names": service.model.names,  # {0: '0', 1: 'Kursi', 2: 'chair', ...}
            "class_index_to_name_mapping": {str(idx): name for idx, name in service.model.names.items()}
        }
        
        detection_result = {
            "detected_classes": result["class_counts"],  # {'chair': 2, ...}
            "total_detections": sum(result["class_counts"].values()),
            "detected_chairs": result["detected_chairs"],
            "frames_with_detections": result.get("frames_with_detections"),
            "num_frames_processed": result["num_frames_processed"],
            "message": result["message"]
        }
        
        # Avisos
        warnings = []
        if "0" in result["class_counts"]:
            warnings.append(
                f"⚠️ Classe '0' foi detectada ({result['class_counts']['0']} vezes). "
                f"No modelo, classe 0 mapeada para: '{service.model.names[0]}'"
            )
        
        if result["detected_chairs"] == 0 and len(result["class_counts"]) > 0:
            detected_chars = list(result["class_counts"].keys())
            warnings.append(
                f"⚠️ Nenhuma cadeira detectada, mas outras classes foram: {detected_chars}"
            )
        
        return {
            "status": "debug_detection",
            "model_info": model_info,
            "detection_result": detection_result,
            "warnings": warnings if warnings else None,
            "hint": "Use 'model_info.class_index_to_name_mapping' para verificar o mapeamento de classes"
        }
        
    except Exception as e:
        logger.error(f"Erro na detecção debug: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))