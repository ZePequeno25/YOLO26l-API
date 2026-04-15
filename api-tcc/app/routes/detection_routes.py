from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from app.models.detection import AnalysisResponse
from app.models.metrics import GroundTruthRequest, LiveMetricsResponse
from app.services.detection_service import DetectionService
from app.services.ollama_message_service import OllamaMessageService
from app.services.live_metrics_service import live_metrics_service
from app.services.metrics_report_service import metrics_report_service
from app.core.firebase import verify_id_token, TokenValidationError, TokenExpiredError
from app.core.analysis_guard import analysis_guard
import logging
import mimetypes
from pathlib import Path
from uuid import uuid4
from fastapi.responses import FileResponse
from urllib.parse import quote

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detection", tags=["Detecção"])

detection_service = DetectionService()
ollama_message_service = OllamaMessageService()


def _extract_token(
    id_token: str | None,
    authorization: str | None,
    access_token: str | None = None,
    token: str | None = None,
    idToken: str | None = None,
    accessToken: str | None = None,
) -> str:
    def _normalize(value: str | None) -> str:
        cleaned = (value or "").strip().strip('"').strip("'")
        while cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip().strip('"').strip("'")
        return cleaned

    for candidate in (id_token, access_token, token, idToken, accessToken):
        if candidate:
            normalized = _normalize(candidate)
            if normalized:
                return normalized

    if authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
            normalized = _normalize(parts[1])
            if normalized:
                return normalized

        # Compatibilidade: Authorization contendo token cru.
        normalized = _normalize(authorization)
        if normalized:
            return normalized

    raise HTTPException(status_code=401, detail="Token ausente. Envie id_token/access_token/token no form-data ou Authorization: Bearer <token>.")

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image_video(
    file: UploadFile = File(...),
    id_token: str | None = Form(None),
    idToken: str | None = Form(None),
    access_token: str | None = Form(None),
    accessToken: str | None = Form(None),
    token: str | None = Form(None),
    authorization: str | None = Header(None),
    model: str = Form(None, description="Nome do modelo a usar (ex: 'chair', 'table'). Se não informado, usa o padrão.")
):
    uid: str | None = None
    lock_acquired = False
    try:
        # Verificar autenticação
        request_token = _extract_token(
            id_token=id_token,
            authorization=authorization,
            access_token=access_token,
            token=token,
            idToken=idToken,
            accessToken=accessToken,
        )
        decoded = verify_id_token(request_token)
        uid = decoded.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Token inválido: uid ausente.")

        analysis_guard.acquire(uid)
        lock_acquired = True
        logger.info(f"Detecção solicitada por: {decoded.get('email')}")
        
        # Analisar arquivo
        result = await detection_service.analyze(file, model)

        # Compatibilidade com clientes que baixam via URL simples (sem header Authorization).
        analyzed_output = result.get("analyzed_output")
        if isinstance(analyzed_output, dict):
            download_url = analyzed_output.get("download_url")
            if isinstance(download_url, str) and download_url:
                encoded_token = quote(request_token, safe="")
                sep = "&" if "?" in download_url else "?"
                analyzed_output["download_url"] = f"{download_url}{sep}token={encoded_token}"

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
    except ValueError as e:
        # Erros de validação do arquivo (duração, formato, tamanho) — Ollama gera mensagem amigável
        logger.warning(f"Erro de validação na análise: {e}")
        friendly = ollama_message_service.generate_error_message(str(e))
        raise HTTPException(status_code=422, detail=friendly)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na detecção: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Não foi possível processar o arquivo. Tente novamente.")
    finally:
        if uid and lock_acquired:
            analysis_guard.release(uid)

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
async def download_analyzed_file(
    filename: str,
    id_token: str | None = None,
    idToken: str | None = None,
    access_token: str | None = None,
    accessToken: str | None = None,
    token: str | None = None,
    authorization: str | None = Header(None),
):
    """Faz download de um arquivo analisado."""
    try:
        request_token = _extract_token(
            id_token=id_token,
            authorization=authorization,
            access_token=access_token,
            token=token,
            idToken=idToken,
            accessToken=accessToken,
        )
        decoded = verify_id_token(request_token)
        logger.info(f"Download solicitado por: {decoded.get('email')}")

        # Validar nome do arquivo para evitar path traversal attacks
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

        file_path = detection_service.output_dir / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {filename}")

        logger.info(f"Download iniciado: {filename}")
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=mime_type
        )
    except (TokenExpiredError, TokenValidationError):
        raise HTTPException(status_code=404, detail="Nao encontrado")
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
        sample_metrics = live_metrics_service.get_sample_metrics(sample_id=payload.sample_id)
        report_path = metrics_report_service.append_sample_metrics(
            sample_metrics,
            source="api_ground_truth",
        )
        return {
            "success": True,
            "message": "Ground truth registrado com sucesso",
            "metrics_saved_to": str(report_path),
            "sample_metrics": sample_metrics,
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