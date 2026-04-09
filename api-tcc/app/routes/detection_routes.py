from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.models.detection import AnalysisResponse
from app.models.metrics import GroundTruthRequest, LiveMetricsResponse
from app.services.detection_service import DetectionService
from app.services.ollama_message_service import OllamaMessageService
from app.services.live_metrics_service import live_metrics_service
from app.core.firebase import verify_id_token, TokenValidationError, TokenExpiredError
import logging
from pathlib import Path
from uuid import uuid4
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detection", tags=["Detecção"])

detection_service = DetectionService()
ollama_message_service = OllamaMessageService()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image_video(
    file: UploadFile = File(...),
    id_token: str = Form(...),
    model: str = Form(None, description="Nome do modelo a usar (ex: 'chair', 'table'). Se não informado, usa o padrão.")
):
    try:
        # Verificar autenticação
        decoded = verify_id_token(id_token)
        logger.info(f"Detecção solicitada por: {decoded.get('email')}")
        
        # Analisar arquivo
        result = await detection_service.analyze(file, model)

        sample_id = f"sample-{uuid4().hex}"
        model_name = result.get("analysis_model_used") or model or "chair"
        personalized_message = ollama_message_service.generate_personalized_message(result, model_name)
        live_metrics_service.add_prediction_sample(
            sample_id=sample_id,
            model_name=model_name,
            predictions=result.get("boxes") or [],
        )
        
        logger.info(f"📊 Resultado final da detecção:")
        logger.info(f"   class_counts: {result['class_counts']}")
        logger.info(f"   detected_chairs: {result['detected_chairs']}")
        logger.info(f"   frames_with_detections: {result.get('frames_with_detections')}")

        return AnalysisResponse(
            success=True,
            message=personalized_message or result.get("message", "Analise concluida com sucesso"),
            personalized_message=personalized_message,
            analysis_model_used=model_name,
            llm_model_used=ollama_message_service.model,
            class_counts=result["class_counts"],
            num_frames_processed=result["num_frames_processed"],
            evaluation_sample_id=sample_id,
            detected_chairs=result["detected_chairs"],
            frames_with_detections=result.get("frames_with_detections"),
            analyzed_file=result.get("analyzed_file"),
            analyzed_output=result.get("analyzed_output"),
            boxes=result.get("boxes")
        )
    except TokenExpiredError as e:
        logger.warning(f"Token expirado em /detection/analyze: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except TokenValidationError as e:
        logger.warning(f"Token inválido em /detection/analyze: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Erro na detecção: {error_detail}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno durante a análise")

@router.post("/analyze-test", response_model=AnalysisResponse)
async def analyze_image_video_test(
    file: UploadFile = File(...),
    model: str = Form(None, description="Nome do modelo a usar (ex: 'chair', 'table'). Se não informado, usa o padrão.")
):
    """Endpoint de teste sem autenticação para análise de imagens/vídeos."""
    try:
        logger.info(f"Detecção solicitada (teste)")
        
        # Analisar arquivo
        result = await detection_service.analyze(file, model)

        sample_id = f"sample-{uuid4().hex}"
        model_name = result.get("analysis_model_used") or model or "chair"
        personalized_message = ollama_message_service.generate_personalized_message(result, model_name)
        live_metrics_service.add_prediction_sample(
            sample_id=sample_id,
            model_name=model_name,
            predictions=result.get("boxes") or [],
        )
        
        logger.info(f"📊 Resultado final da detecção:")
        logger.info(f"   class_counts: {result['class_counts']}")
        logger.info(f"   detected_chairs: {result['detected_chairs']}")

        return AnalysisResponse(
            success=True,
            message=personalized_message or result.get("message", "Analise concluida com sucesso"),
            personalized_message=personalized_message,
            analysis_model_used=model_name,
            llm_model_used=ollama_message_service.model,
            class_counts=result["class_counts"],
            num_frames_processed=result["num_frames_processed"],
            evaluation_sample_id=sample_id,
            detected_chairs=result["detected_chairs"],
            frames_with_detections=result.get("frames_with_detections"),
            analyzed_file=result.get("analyzed_file"),
            analyzed_output=result.get("analyzed_output"),
            boxes=result.get("boxes")
        )
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Erro na detecção: {error_detail}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/models")
async def list_models():
    """Lista modelos disponíveis para detecção."""
    try:
        models = detection_service.list_available_models()
        return {
            "success": True,
            "models": models,
            "default_model": "chair"
        }
    except Exception as e:
        logger.error(f"Erro ao listar modelos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_analyzed_file(filename: str, id_token: str = None):
    """Faz download de um arquivo analisado."""
    try:
        # Verificar autenticação se token foi fornecido
        if id_token:
            try:
                decoded = verify_id_token(id_token)
                logger.info(f"Download solicitado por: {decoded.get('email')}")
            except Exception as auth_err:
                logger.warning(f"Autenticação falhou: {auth_err}")
                # Continuar mesmo sem autenticação para arquivos públicos

        # Validar nome do arquivo para evitar path traversal attacks
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

        file_path = detection_service.output_dir / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {filename}")

        logger.info(f"Download iniciado: {filename}")
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics/ground-truth")
async def submit_ground_truth(payload: GroundTruthRequest):
    """Recebe ground truth para uma amostra e consolida no avaliador online."""
    try:
        result = live_metrics_service.add_ground_truth(
            sample_id=payload.sample_id,
            model_name=payload.model_name,
            ground_truth=[item.model_dump() for item in payload.boxes],
        )
        return {
            "success": True,
            "message": "Ground truth registrado com sucesso",
            **result,
        }
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error(f"Erro ao registrar ground truth: {err}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao registrar ground truth")


@router.get("/metrics/live", response_model=LiveMetricsResponse)
async def get_live_metrics(window_seconds: int = 300, iou_threshold: float = 0.5):
    """Retorna precisão, recall e mAP em janela deslizante recente."""
    try:
        live_metrics_service.set_window(window_seconds)
        metrics = live_metrics_service.get_live_metrics(iou_threshold=iou_threshold)
        return LiveMetricsResponse(**metrics)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error(f"Erro ao calcular métricas online: {err}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao calcular métricas")


@router.post("/metrics/reset")
async def reset_live_metrics():
    """Limpa buffer de avaliação online e estado pendente."""
    live_metrics_service.reset()
    return {
        "success": True,
        "message": "Métricas em tempo real resetadas",
    }