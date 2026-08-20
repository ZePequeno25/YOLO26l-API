"""
Detection routes module.
Handles image and video object detection (e.g. chairs), ground truth submission,
and live metrics evaluation.
"""
# pylint: disable=too-many-arguments, too-many-locals, too-many-statements, invalid-name
import base64
import gzip
import logging
import mimetypes
from typing import Optional
from urllib.parse import quote
from uuid import uuid4

import asyncio
import cv2
import json
import numpy as np
from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, Query, Request, UploadFile, Response
from fastapi.responses import FileResponse, StreamingResponse
from config.settings import settings

from app.core.analysis_guard import analysis_guard
from app.core.firebase import (
    TokenExpiredError,
    TokenValidationError,
    verify_id_token,
)
from app.models.detection import AnalysisResponse
from app.models.metrics import GroundTruthRequest, LiveMetricsResponse
from app.services.detection_service import DetectionService
from app.services.live_metrics_service import live_metrics_service
from app.services.metrics_report_service import metrics_report_service
from app.services.ollama_message_service import OllamaMessageService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detection", tags=["Detecção"])

detection_service = DetectionService()
ollama_message_service = OllamaMessageService()


async def run_background_analysis(
    job_id: str,
    saved_file_path: str,
    original_filename: str,
    content_type: str,
    model: Optional[str]
):
    try:
        detection_service.update_job_status(job_id, "PROCESSANDO")
        
        # Envelopar o arquivo salvo em um UploadFile do Starlette
        from fastapi import UploadFile
        with open(saved_file_path, "rb") as f:
            upload_file = UploadFile(
                file=f,
                filename=original_filename,
                headers={"content-type": content_type}
            )
            result = await detection_service.analyze(upload_file, model)

        # Montar a resposta padrão
        sample_id = f"sample-{uuid4().hex}"
        default_model = getattr(detection_service, 'default_model', "cadeira")
        requested_model = result.get("requested_model") or model or default_model

        # Gerar mensagem personalizada via Ollama (não-bloqueante com timeout de 8s)
        try:
            personalized_message = await asyncio.wait_for(
                asyncio.to_thread(
                    ollama_message_service.generate_personalized_message,
                    result,
                    requested_model
                ),
                timeout=8.0
            )
        except Exception as ollama_err:
            logger.warning("⚠️ Mensagem Ollama em background indisponível/timeout: %s", ollama_err)
            personalized_message = ollama_message_service._build_fallback_message(result, requested_model)

        live_metrics_service.add_prediction_sample(
            sample_id=sample_id,
            model_name=requested_model,
            predictions=result.get("boxes") or [],
        )

        detected_chairs = result["class_counts"].get(
            "cadeira", result["class_counts"].get("chair", 0)
        )

        response_data = {
            "success": True,
            "message": personalized_message or "Análise concluída.",
            "personalized_message": personalized_message,
            "analysis_model_used": requested_model,
            "requested_model": requested_model,
            "llm_model_used": ollama_message_service.model,
            "class_counts": result["class_counts"],
            "num_frames_processed": result["num_frames_processed"],
            "evaluation_sample_id": sample_id,
            "detected_chairs": detected_chairs,
            "frames_with_detections": result.get("frames_with_detections"),
            "analyzed_file": result.get("analyzed_file"),
            "analyzed_output": result.get("analyzed_output"),
            "boxes": result.get("boxes"),
            "compliance_status": result.get("compliance_status"),
            "compliance_alerts": result.get("compliance_alerts"),
            "compliance_report": result.get("compliance_report"),
            "job_id": job_id,
            "status": "CONCLUIDO"
        }

        detection_service.update_job_status(job_id, "CONCLUIDO", result=response_data)

    except Exception as e:
        logger.error("Falha no processamento assíncrono do Job %s: %s", job_id, e, exc_info=True)
        detection_service.update_job_status(job_id, "FALHADO", error=str(e))
    finally:
        # Remover o arquivo salvo temporariamente
        try:
            import os
            if os.path.exists(saved_file_path):
                os.unlink(saved_file_path)
        except Exception as cleanup_err:
            logger.warning("Falha ao remover arquivo temporário do Job %s: %s", job_id, cleanup_err)


def _extract_token(
    id_token: Optional[str],
    authorization: Optional[str],
    access_token: Optional[str] = None,
    token: Optional[str] = None,
    idToken: Optional[str] = None,
    accessToken: Optional[str] = None,
) -> str:
    """Extracts and normalizes the authentication token from candidate parameters/headers."""
    def _normalize(value: Optional[str]) -> str:
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

    raise HTTPException(
        status_code=401,
        detail=(
            "Token ausente. Envie id_token/access_token/token "
            "no form-data ou Authorization: Bearer <token>."
        )
    )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image_video(
    background_tasks: BackgroundTasks,
    response: Response,
    file: UploadFile = File(...),
    id_token: Optional[str] = Form(None),
    idToken: Optional[str] = Form(None),
    access_token: Optional[str] = Form(None),
    accessToken: Optional[str] = Form(None),
    token: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    model: str = Form(None, description="Nome do modelo a usar. Se não informado, usa o padrão."),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
):
    """
    Analyzes an uploaded image or video using the specified object detection model.
    """
    # 1. Verificação de Idempotência com X-Request-ID
    if x_request_id:
        existing_job_id = detection_service.get_job_id_by_request_id(x_request_id)
        if existing_job_id:
            job = detection_service.get_job(existing_job_id)
            if job:
                status = job["status"]
                logger.info("♻️ Idempotência acionada para X-Request-ID: %s. Status do Job %s: %s", x_request_id, existing_job_id, status)
                if status == "CONCLUIDO":
                    return job["result"]
                elif status == "FALHADO":
                    raise HTTPException(
                        status_code=500,
                        detail=f"Falha no processamento anterior associado a esta requisição: {job['error']}"
                    )
                else:
                    response.status_code = 202
                    return AnalysisResponse(
                        success=True,
                        message=f"Solicitação duplicada (X-Request-ID). Processamento em andamento. Status atual: {status}.",
                        class_counts={},
                        num_frames_processed=0,
                        job_id=existing_job_id,
                        status=status
                    )

    if settings.ASYNC_QUEUE_MODE:
        import os
        import shutil
        from pathlib import Path
        
        job_id = f"job-{uuid4().hex}"
        uploads_dir = Path("data/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        suffix = Path(file.filename).suffix.lower()
        if not suffix:
            suffix = ".jpg"
        saved_file_path = str(uploads_dir / f"{job_id}{suffix}")
        
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        try:
            detection_service.create_job(job_id)
            if x_request_id:
                detection_service.register_request_id(x_request_id, job_id)
        except ValueError as val_err:
            import os
            if os.path.exists(saved_file_path):
                os.unlink(saved_file_path)
            raise HTTPException(status_code=429, detail=str(val_err))

        background_tasks.add_task(
            run_background_analysis,
            job_id,
            saved_file_path,
            file.filename,
            file.content_type or "image/jpeg",
            model
        )
        
        response.status_code = 202
        return AnalysisResponse(
            success=True,
            message="Solicitação recebida e enviada para a fila de processamento.",
            class_counts={},
            num_frames_processed=0,
            job_id=job_id,
            status="PENDENTE"
        )
    uid: Optional[str] = None
    lock_acquired = False
    sync_job_id = None
    if x_request_id:
        sync_job_id = f"job-sync-{uuid4().hex}"
        try:
            detection_service.create_job(sync_job_id)
            detection_service.register_request_id(x_request_id, sync_job_id)
            detection_service.update_job_status(sync_job_id, "PROCESSANDO")
        except Exception:
            pass

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
        logger.info("Detecção solicitada por: %s", decoded.get("email"))

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
        default_model = getattr(detection_service, 'default_model', "cadeira")
        requested_model = result.get("requested_model") or model or default_model

        # Gerar mensagem via Ollama com base no modelo pedido vs encontrados (não-bloqueante)
        try:
            personalized_message = await asyncio.wait_for(
                asyncio.to_thread(
                    ollama_message_service.generate_personalized_message,
                    result,
                    requested_model
                ),
                timeout=8.0
            )
        except Exception as ollama_err:
            logger.warning("⚠️ Mensagem Ollama indisponível ou timeout (8s): %s", ollama_err)
            personalized_message = ollama_message_service._build_fallback_message(result, requested_model)

        live_metrics_service.add_prediction_sample(
            sample_id=sample_id,
            model_name=requested_model,
            predictions=result.get("boxes") or [],
        )

        # Obter número de cadeiras (legacy field compatibility)
        detected_chairs = result["class_counts"].get(
            "cadeira", result["class_counts"].get("chair", 0)
        )

        logger.info("📊 Resultado final da detecção:")
        logger.info("   class_counts: %s", result["class_counts"])
        logger.info("   requested_model: %s", requested_model)
        logger.info("   frames_with_detections: %s", result.get("frames_with_detections"))

        resp = AnalysisResponse(
            success=True,
            message=personalized_message or "Análise concluída.",
            personalized_message=personalized_message,
            analysis_model_used=requested_model,
            requested_model=requested_model,
            llm_model_used=ollama_message_service.model,
            class_counts=result["class_counts"],
            num_frames_processed=result["num_frames_processed"],
            evaluation_sample_id=sample_id,
            detected_chairs=detected_chairs,
            frames_with_detections=result.get("frames_with_detections"),
            analyzed_file=result.get("analyzed_file"),
            analyzed_output=result.get("analyzed_output"),
            boxes=result.get("boxes"),
            compliance_status=result.get("compliance_status"),
            compliance_alerts=result.get("compliance_alerts"),
            compliance_report=result.get("compliance_report"),
        )
        if sync_job_id:
            detection_service.update_job_status(sync_job_id, "CONCLUIDO", result=resp)
        return resp
    except TokenExpiredError as e:
        if sync_job_id:
            detection_service.update_job_status(sync_job_id, "FALHADO", error=str(e))
        logger.warning("Token expirado em /detection/analyze: %s", e)
        raise HTTPException(status_code=401, detail=str(e)) from e
    except TokenValidationError as e:
        if sync_job_id:
            detection_service.update_job_status(sync_job_id, "FALHADO", error=str(e))
        logger.warning("Token inválido em /detection/analyze: %s", e)
        raise HTTPException(status_code=401, detail=str(e)) from e
    except ValueError as e:
        try:
            friendly = await asyncio.wait_for(
                asyncio.to_thread(ollama_message_service.generate_error_message, str(e)),
                timeout=5.0
            )
        except Exception:
            friendly = ollama_message_service._build_fallback_error_message(str(e))
        if sync_job_id:
            detection_service.update_job_status(sync_job_id, "FALHADO", error=friendly)
        logger.warning("Erro de validação na análise: %s", e)
        raise HTTPException(status_code=422, detail=friendly) from e
    except HTTPException as http_exc:
        if sync_job_id:
            detection_service.update_job_status(sync_job_id, "FALHADO", error=str(http_exc.detail))
        raise
    except Exception as e:
        if sync_job_id:
            detection_service.update_job_status(sync_job_id, "FALHADO", error=str(e))
        logger.error("Erro na detecção: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Não foi possível processar o arquivo. Tente novamente."
        ) from e
    finally:
        if uid and lock_acquired:
            analysis_guard.release(uid)


@router.post("/analyze-test", response_model=AnalysisResponse)
async def analyze_image_video_test(
    background_tasks: BackgroundTasks,
    response: Response,
    file: UploadFile = File(...),
    model: str = Form(None, description="Nome do modelo a usar. Se não informado, usa o padrão."),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
):
    """Endpoint de teste sem autenticação para análise de imagens/vídeos."""
    # 1. Verificação de Idempotência com X-Request-ID
    if x_request_id:
        existing_job_id = detection_service.get_job_id_by_request_id(x_request_id)
        if existing_job_id:
            job = detection_service.get_job(existing_job_id)
            if job:
                status = job["status"]
                logger.info("♻️ Idempotência acionada para X-Request-ID (teste): %s. Status do Job %s: %s", x_request_id, existing_job_id, status)
                if status == "CONCLUIDO":
                    return job["result"]
                elif status == "FALHADO":
                    raise HTTPException(
                        status_code=500,
                        detail=f"Falha no processamento anterior associado a esta requisição: {job['error']}"
                    )
                else:
                    response.status_code = 202
                    return AnalysisResponse(
                        success=True,
                        message=f"Solicitação duplicada (X-Request-ID). Processamento em andamento. Status atual: {status}.",
                        class_counts={},
                        num_frames_processed=0,
                        job_id=existing_job_id,
                        status=status
                    )

    if settings.ASYNC_QUEUE_MODE:
        import os
        import shutil
        from pathlib import Path
        
        job_id = f"job-{uuid4().hex}"
        uploads_dir = Path("data/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        suffix = Path(file.filename).suffix.lower()
        if not suffix:
            suffix = ".jpg"
        saved_file_path = str(uploads_dir / f"{job_id}{suffix}")
        
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        try:
            detection_service.create_job(job_id)
            if x_request_id:
                detection_service.register_request_id(x_request_id, job_id)
        except ValueError as val_err:
            import os
            if os.path.exists(saved_file_path):
                os.unlink(saved_file_path)
            raise HTTPException(status_code=429, detail=str(val_err))

        background_tasks.add_task(
            run_background_analysis,
            job_id,
            saved_file_path,
            file.filename,
            file.content_type or "image/jpeg",
            model
        )
        
        response.status_code = 202
        return AnalysisResponse(
            success=True,
            message="Solicitação recebida e enviada para a fila de processamento.",
            class_counts={},
            num_frames_processed=0,
            job_id=job_id,
            status="PENDENTE"
        )

    sync_job_id = None
    if x_request_id:
        sync_job_id = f"job-sync-test-{uuid4().hex}"
        try:
            detection_service.create_job(sync_job_id)
            detection_service.register_request_id(x_request_id, sync_job_id)
            detection_service.update_job_status(sync_job_id, "PROCESSANDO")
        except Exception:
            pass

    try:
        logger.info("Detecção solicitada (teste)")

        # Analisar arquivo
        result = await detection_service.analyze(file, model)

        sample_id = f"sample-{uuid4().hex}"
        default_model = getattr(detection_service, 'default_model', "cadeira")
        requested_model = result.get("requested_model") or model or default_model

        try:
            personalized_message = await asyncio.wait_for(
                asyncio.to_thread(
                    ollama_message_service.generate_personalized_message,
                    result,
                    requested_model
                ),
                timeout=8.0
            )
        except Exception as ollama_err:
            logger.warning("⚠️ Mensagem Ollama (teste) indisponível ou timeout (8s): %s", ollama_err)
            personalized_message = ollama_message_service._build_fallback_message(result, requested_model)

        live_metrics_service.add_prediction_sample(
            sample_id=sample_id,
            model_name=requested_model,
            predictions=result.get("boxes") or [],
        )

        detected_chairs = result["class_counts"].get(
            "cadeira", result["class_counts"].get("chair", 0)
        )

        logger.info("📊 Resultado final da detecção:")
        logger.info("   class_counts: %s", result["class_counts"])
        logger.info("   requested_model: %s", requested_model)

        resp = AnalysisResponse(
            success=True,
            message=personalized_message or "Análise concluída.",
            personalized_message=personalized_message,
            analysis_model_used=requested_model,
            requested_model=requested_model,
            llm_model_used=ollama_message_service.model,
            class_counts=result["class_counts"],
            num_frames_processed=result["num_frames_processed"],
            evaluation_sample_id=sample_id,
            detected_chairs=detected_chairs,
            frames_with_detections=result.get("frames_with_detections"),
            analyzed_file=result.get("analyzed_file"),
            analyzed_output=result.get("analyzed_output"),
            boxes=result.get("boxes"),
            compliance_status=result.get("compliance_status"),
            compliance_alerts=result.get("compliance_alerts"),
            compliance_report=result.get("compliance_report"),
        )
        if sync_job_id:
            detection_service.update_job_status(sync_job_id, "CONCLUIDO", result=resp)
        return resp
    except Exception as e:
        error_detail = str(e)
        if sync_job_id:
            detection_service.update_job_status(sync_job_id, "FALHADO", error=error_detail)
        logger.error("Erro na detecção: %s", error_detail, exc_info=True)
        raise HTTPException(status_code=500, detail=error_detail) from e


@router.get("/models")
async def list_models():
    """Lista modelos disponíveis para detecção."""
    try:
        models = detection_service.list_available_models()
        return {
            "success": True,
            "models": models,
            "default_model": getattr(detection_service, "default_model", "cadeira")
        }
    except Exception as e:
        logger.error("Erro ao listar modelos: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/download/{filename}")
async def download_analyzed_file(
    filename: str,
    id_token: Optional[str] = None,
    idToken: Optional[str] = None,
    access_token: Optional[str] = None,
    accessToken: Optional[str] = None,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None),
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
        logger.info("Download solicitado por: %s", decoded.get("email"))

        # Validar nome do arquivo para evitar path traversal attacks
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

        file_path = detection_service.output_dir / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {filename}")

        logger.info("Download iniciado: %s", filename)
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=mime_type
        )
    except (TokenExpiredError, TokenValidationError) as exc:
        raise HTTPException(status_code=404, detail="Nao encontrado") from exc
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao fazer download: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        logger.error("Erro ao registrar ground truth: %s", err, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Erro interno ao registrar ground truth"
        ) from err


@router.get("/metrics/live", response_model=LiveMetricsResponse)
async def get_live_metrics(window_seconds: int = 300, iou_threshold: float = 0.5):
    """Retorna precisão, recall e mAP em janela deslizante recente."""
    try:
        live_metrics_service.set_window(window_seconds)
        metrics = live_metrics_service.get_live_metrics(iou_threshold=iou_threshold)
        return LiveMetricsResponse(**metrics)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        logger.error("Erro ao calcular métricas online: %s", err, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao calcular métricas") from err


@router.post("/metrics/reset")
async def reset_live_metrics():
    """Limpa buffer de avaliação online e estado pendente."""
    live_metrics_service.reset()
    return {
        "success": True,
        "message": "Métricas em tempo real resetadas",
    }


@router.post("/frame")
async def process_single_frame(
    request: Request,
    model: Optional[str] = Query(None),
    min_confidence: float = Query(0.25),
    disable_compliance: bool = Query(True),
    imgsz: int = Query(640, description="Resolução otimizada para tempo real (padrão 640 para compatibilidade com OpenVINO)"),
):
    """
    Endpoint ultra-rápido em memória para processar quadros individuais transmitidos
    pela câmera do celular Android em tempo real (aceita tanto bytes puros no corpo quanto multipart/form-data).
    """
    try:
        raw_body = await request.body()
        if not raw_body:
            raise HTTPException(status_code=400, detail="Corpo da requisição vazio.")

        # Descompacta automaticamente se os dados vierem compactados com GZIP (magic bytes 0x1f 0x8b)
        if raw_body.startswith(b"\x1f\x8b"):
            try:
                raw_body = gzip.decompress(raw_body)
            except Exception as gz_err:
                logger.warning("⚠️ Falha ao descompactar GZIP: %s", gz_err)

        frame = None

        # 1. Tenta decodificar como imagem binária direta (JPEG/PNG bytes)
        nparr = np.frombuffer(raw_body, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 2. Se a imagem estiver dentro de multipart/headers, localiza a assinatura mágica do JPEG (\xff\xd8\xff) ou PNG
        if frame is None:
            jpeg_idx = raw_body.find(b"\xff\xd8\xff")
            if jpeg_idx != -1:
                frame = cv2.imdecode(np.frombuffer(raw_body[jpeg_idx:], np.uint8), cv2.IMREAD_COLOR)

        if frame is None:
            png_idx = raw_body.find(b"\x89PNG")
            if png_idx != -1:
                frame = cv2.imdecode(np.frombuffer(raw_body[png_idx:], np.uint8), cv2.IMREAD_COLOR)

        # 3. Se falhou, tenta decodificar como Base64 (string pura ou data URI)
        if frame is None:
            try:
                text_content = raw_body.decode("utf-8", errors="ignore").strip()
                b64_str = ""
                if text_content.startswith("{"):
                    data = json.loads(text_content)
                    b64_str = data.get("image") or data.get("frame") or data.get("data") or ""
                    model = data.get("model") or model
                else:
                    b64_str = text_content

                if "base64," in b64_str:
                    b64_str = b64_str.split("base64,")[1]

                if b64_str:
                    decoded_bytes = base64.b64decode(b64_str)
                    nparr = np.frombuffer(decoded_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as b64_err:
                logger.debug("Tentativa de decodificação Base64/JSON falhou: %s", b64_err)

        # 4. Se falhou, tenta extrair de multipart/form-data
        if frame is None:
            try:
                form = await request.form()
                upload_file = form.get("file")
                if upload_file and hasattr(upload_file, "read"):
                    file_bytes = await upload_file.read()
                    nparr = np.frombuffer(file_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    model = form.get("model") or model
            except Exception as form_err:
                logger.debug("Tentativa de extração multipart falhou: %s", form_err)

        if frame is None:
            raise HTTPException(status_code=400, detail="Não foi possível decodificar a imagem do quadro (formato de bytes/base64 não reconhecido).")

        result = await detection_service.analyze_frame(
            frame,
            frame_index=0,
            model_name=model,
            min_confidence=min_confidence,
            disable_compliance=disable_compliance,
            imgsz=imgsz,
        )

        logger.info("🎯 [INFERÊNCIA CONCLUÍDA] Caixas encontradas: %d | Contagem por classe: %s",
                    len(result["boxes"]), dict(result["class_counts"]))

        return {
            "success": True,
            "class_counts": result["class_counts"],
            "boxes": result["boxes"],
            "compliance_status": result["compliance_status"],
            "compliance_alerts": result["compliance_alerts"],
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error("Erro ao processar quadro em tempo real: %s", err, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar quadro") from err


@router.get("/stream")
async def stream_realtime_detections(
    video_source: str,
    frame_stride: int = 1,
    min_confidence: float = Query(default=0.25, ge=0.0, le=1.0, help="Limiar mínimo de certeza para exibir caixas (0.25 = 25%)"),
    disable_compliance: bool = Query(default=True, help="Desativa verificação de regras de conformidade para máxima velocidade em tempo real"),
    imgsz: int = Query(default=640, help="Resolução de inferência (padrão 640 para compatibilidade com modelos OpenVINO)"),
    model: Optional[str] = None,
    id_token: Optional[str] = None,
    idToken: Optional[str] = None,
    access_token: Optional[str] = None,
    accessToken: Optional[str] = None,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Rota para predição em tempo real que abre um fluxo de vídeo e retorna
    as detecções, métricas de certeza das caixas e status de conformidade via Server-Sent Events (SSE).
    """
    # Verificação opcional de autenticação para simplificar testes no Android Studio
    try:
        req_token = _extract_token(
            id_token=id_token,
            authorization=authorization,
            access_token=access_token,
            token=token,
            idToken=idToken,
            accessToken=accessToken,
        )
        decoded = verify_id_token(req_token)
        logger.info("Stream em tempo real solicitado por: %s", decoded.get("email"))
    except Exception:
        logger.info("Stream em tempo real rodando sem autenticação (ou token opcional).")

    async def frame_generator():
        # Se for apenas dígitos, abre a câmera/webcam correspondente
        source = int(video_source) if video_source.isdigit() else video_source
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error("Não foi possível abrir o fluxo de vídeo: %s", video_source)
            yield f"data: {json.dumps({'error': f'Não foi possível abrir o fluxo: {video_source}'})}\n\n"
            return

        logger.info("🎥 Fluxo de vídeo '%s' aberto com sucesso.", video_source)
        frame_idx = 0
        consecutive_failures = 0

        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    consecutive_failures += 1
                    # Tolerância de 10 segundos de queda temporária de frames (RTSP/Lives)
                    if consecutive_failures > 100:
                        logger.info("🎥 Conexão com a fonte do vídeo perdida permanentemente.")
                        break
                    await asyncio.sleep(0.1)
                    continue

                consecutive_failures = 0

                if frame_idx % max(1, frame_stride) == 0:
                    # Executa inferência do modelo solicitado ou de todos se omitido
                    result = await detection_service.analyze_frame(
                        frame,
                        frame_index=frame_idx,
                        model_name=model,
                        min_confidence=min_confidence,
                        disable_compliance=disable_compliance,
                        imgsz=imgsz,
                    )
                    payload = {
                        "frame_index": frame_idx,
                        "class_counts": result["class_counts"],
                        "boxes": result["boxes"],
                        "compliance_status": result["compliance_status"],
                        "compliance_alerts": result["compliance_alerts"]
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                frame_idx += 1
                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info("🔌 Stream de vídeo cancelado pelo cliente (conexão fechada).")
        finally:
            cap.release()
            logger.info("🎥 Captura de fluxo de vídeo fechada.")

    return StreamingResponse(frame_generator(), media_type="text/event-stream")


@router.get("/job/{job_id}", response_model=AnalysisResponse)
@router.get("/status/{job_id}", response_model=AnalysisResponse)
async def get_job_status(job_id: str, response: Response):
    """
    Endpoint para consulta de status e resultado final de análises assíncronas (polling).
    """
    job = detection_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    status = job["status"]
    if status == "CONCLUIDO":
        return job["result"]
    elif status == "FALHADO":
        raise HTTPException(
            status_code=500,
            detail=f"Falha no processamento da análise: {job['error']}"
        )
    else:
        # PENDENTE ou PROCESSANDO
        response.status_code = 202
        return AnalysisResponse(
            success=True,
            message=f"Processando... Aguarde. (Status atual: {status})",
            class_counts={},
            num_frames_processed=0,
            job_id=job_id,
            status=status
        )