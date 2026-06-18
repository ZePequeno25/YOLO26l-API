"""
Detection service module.
Manages loading YOLO models, caching them, running inference on images and videos,
deduplicating bounding boxes, drawing detection results, and saving training artifacts.
"""
# pylint: disable=too-many-instance-attributes, too-many-locals, too-many-branches, too-many-statements
from collections import defaultdict
from datetime import datetime
import logging
import os
from pathlib import Path
import re
from uuid import uuid4

import cv2
from fastapi import UploadFile
import numpy as np
from ultralytics import YOLO

from app.utils.test_simulator import simulate_video_from_image
from config.settings import settings

logger = logging.getLogger(__name__)


class DetectionService:
    """
    Service class that handles YOLO-based object detection,
    coordinate mapping, deduplication, and result rendering.
    """
    def __init__(self):
        # Caminho absoluto para o diretório de modelos
        self.models_dir = (
            Path(__file__).resolve().parent.parent.parent.parent / "models"
        )
        # Diretório para salvar arquivos analisados
        self.output_dir = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "analyzed_outputs"
        )
        self.output_dir.mkdir(exist_ok=True)
        # Diretórios para armazenar dados recebidos e frames para treino
        self.training_dir = Path(settings.TRAINING_ARTIFACTS_DIR)
        self.training_uploads_images_dir = self.training_dir / "uploads" / "images"
        self.training_uploads_videos_dir = self.training_dir / "uploads" / "videos"
        self.training_video_frames_dir = self.training_dir / "video_frames"
        self.training_uploads_images_dir.mkdir(parents=True, exist_ok=True)
        self.training_uploads_videos_dir.mkdir(parents=True, exist_ok=True)
        self.training_video_frames_dir.mkdir(parents=True, exist_ok=True)
        self.models_cache = {}  # Cache de modelos carregados
        print(f"📁 Diretório de modelos: {self.models_dir}")
        print(f"💾 Diretório de saída: {self.output_dir}")
        print(f"🗃️ Diretório de artefatos de treino: {self.training_dir}")

        # Busca inicial de modelos disponíveis
        self.available_models = self.list_available_models()
        models_str = ", ".join(self.available_models) if self.available_models else "Nenhum"
        print(f"🔍 Modelos encontrados: {models_str}")

        self.default_model = "cadeira"
        if self.default_model not in self.available_models and self.available_models:
            self.default_model = self.available_models[0]
            print(
                f"⚠️ Modelo padrão 'cadeira' não encontrado. "
                f"Usando '{self.default_model}' como padrão."
            )
        elif not self.available_models:
            print("⚠️ AVISO CRÍTICO: Nenhum modelo encontrado na pasta models!")

        print(f"✅ Serviço de detecção inicializado! (Modelo padrão: {self.default_model})")

    def get_model(self, model_name: str = None) -> YOLO:
        """Carrega ou retorna modelo do cache."""
        if model_name is None:
            model_name = getattr(self, 'default_model', "cadeira")  # Modelo padrão dinâmico

        model_name = self._validate_model_name(model_name)

        if model_name in self.models_cache:
            return self.models_cache[model_name]

        # Procurar modelo na pasta correspondente
        model_folder = self.models_dir / model_name
        if not model_folder.exists():
            raise ValueError(f"Modelo '{model_name}' não encontrado em {model_folder}")

        # Procurar arquivo .pt
        pt_files = list(model_folder.glob("*.pt"))
        if not pt_files:
            raise ValueError(f"Nenhum arquivo .pt encontrado em {model_folder}")

        model_path = pt_files[0]  # Usar o primeiro encontrado
        print(f"🔄 Carregando modelo: {model_path}")

        try:
            model = YOLO(str(model_path))
            self.models_cache[model_name] = model
            print(f"✅ Modelo '{model_name}' carregado! Classes: {model.names}")
            return model
        except Exception as e:
            raise ValueError(f"Erro ao carregar modelo '{model_name}': {e}") from e

    @staticmethod
    def _validate_model_name(model_name: str) -> str:
        """Validates that a model name is clean and safe from path traversal."""
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Nome de modelo invalido")

        clean_name = model_name.strip()
        if len(clean_name) > 64:
            raise ValueError("Nome de modelo invalido: muito longo")

        # Permite apenas nomes seguros para evitar path traversal e caracteres especiais.
        if not re.fullmatch(r"[A-Za-z0-9_-]+", clean_name):
            raise ValueError("Nome de modelo invalido: use apenas letras, numeros, _ e -")

        return clean_name

    def list_available_models(self) -> list[str]:
        """Lista modelos disponíveis."""
        if not self.models_dir.exists():
            return []

        models = []
        for folder in self.models_dir.iterdir():
            if folder.is_dir() and not folder.name.startswith('.'):
                pt_files = list(folder.glob("*.pt"))
                if pt_files:
                    models.append(folder.name)
        return sorted(models)

    async def analyze(self, file: UploadFile, model_name: str = None) -> dict:
        """
        Processes an uploaded image or video, running inference with YOLO
        and generating personal summaries.
        """
        requested_model = self._validate_model_name(
            model_name or getattr(self, 'default_model', "cadeira")
        )

        # Obter extensão do nome do arquivo
        suffix = os.path.splitext(file.filename)[1].lower()

        # Se não houver extensão no nome, tentar obter do Content-Type
        if not suffix:
            content_type = file.content_type or ""
            # Mapear Content-Type para extensão
            content_type_map = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/bmp": ".bmp",
                "image/gif": ".gif",
                "image/webp": ".webp",
                "video/mp4": ".mp4",
                "video/quicktime": ".mov",
                "video/x-msvideo": ".avi",
                "video/x-matroska": ".mkv",
                "video/webm": ".webm"
            }
            suffix = content_type_map.get(content_type, "")

        if not suffix:
            suffix = ".jpg"  # Fallback

        content = await file.read()

        # Criar arquivo temporário para análise
        tmp_path = f"temp_{uuid4().hex}{suffix}"

        try:
            if not content:
                raise ValueError("Arquivo vazio recebido")

            # Verificar tamanho (máx 500 MB)
            file_size_mb = len(content) / (1024 * 1024)
            if file_size_mb > 500:
                raise ValueError(f"Arquivo muito grande: {file_size_mb:.1f} MB (máx: 500 MB)")

            # Salvar arquivo
            with open(tmp_path, "wb") as f:
                f.write(content)

            logger.info("✓ Arquivo salvo: %s (%.1f MB)", tmp_path, file_size_mb)

            # Detectar tipo real usando magic bytes
            file_type = self._detect_file_type_from_bytes(content[:20])
            logger.info("✓ Tipo detectado: %s", file_type)

            # Decidir se é vídeo por extensão e/ou magic bytes
            video_extensions = [".mp4", ".mov", ".avi", ".mkv"]
            image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
            is_video = suffix in video_extensions or file_type in ["MP4/MOV", "AVI/WAV", "MKV"]
            is_image = (
                suffix in image_extensions
                or file_type in ["JPEG", "PNG", "GIF87", "GIF89", "WEBP"]
            )

            # Salvar sempre os arquivos recebidos para possível reuso em treino.
            if settings.SAVE_TRAINING_ARTIFACTS:
                self._save_training_artifacts(content, file.filename, suffix, is_video)

            # --- BLOCO DE TESTE: SIMULAR 20 FRAMES PARA IMAGENS ---
            if is_image:
                simulated_video = simulate_video_from_image(tmp_path)
                if simulated_video:
                    tmp_path = simulated_video
                    is_image = False
                    is_video = True
            # ------------------------------------------------------

            # Validar duração máxima de vídeo
            if is_video:
                cap = cv2.VideoCapture(tmp_path)
                fps = cap.get(cv2.CAP_PROP_FPS) or 0
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                cap.release()
                duration_sec = (frame_count / fps) if fps > 0 else 0
                max_duration = settings.MAX_VIDEO_DURATION_SECONDS
                if duration_sec > max_duration:
                    raise ValueError(
                        f"Vídeo muito longo: {duration_sec:.1f}s (máx: {max_duration}s). "
                        f"Envie um clipe de até {max_duration} segundos."
                    )
                logger.info("✓ Duração do vídeo: %.1fs", duration_sec)

            # Variáveis agregadoras para múltiplos modelos
            all_detection_boxes = []
            global_class_counts = defaultdict(int)
            global_unique_objects = defaultdict(set)
            global_frames_with_detections = 0
            total_frames_processed = 0

            # Iterar todos os modelos disponíveis
            for current_model_name in self.available_models:
                logger.info("🤖 Executando modelo: %s", current_model_name)
                model = self.get_model(current_model_name)

                # Suporta imagem e vídeo; para vídeo, tentamos track + fallback frame-by-frame
                if is_video:
                    try:
                        results = list(model.track(
                            source=tmp_path,
                            device=settings.INFERENCE_DEVICE,
                            verbose=False,
                            persist=True,
                            stream=True,  # Evita acumular na RAM
                            vid_stride=max(1, settings.VIDEO_INFERENCE_STRIDE),
                            conf=settings.DETECTION_CONF_THRESHOLD,
                            iou=settings.DETECTION_IOU_THRESHOLD,
                        ))
                        logger.info("  ✓ Vídeo processado via track: %d frames", len(results))
                    except Exception as ex_track:  # pylint: disable=broad-exception-caught
                        logger.warning(
                            "  ⚠️ track() falhou para vídeo: %s. Tentando frame-a-frame",
                            ex_track
                        )
                        results = self._process_video_frames(tmp_path, model)
                        logger.info(
                            "  ✓ Vídeo processado frame-a-frame: %d frames", len(results)
                        )
                else:
                    try:
                        results = list(model(
                            tmp_path,
                            device=settings.INFERENCE_DEVICE,
                            verbose=False,
                            stream=True,  # Evita acumular na RAM
                            conf=settings.DETECTION_CONF_THRESHOLD,
                            iou=settings.DETECTION_IOU_THRESHOLD,
                        ))
                        logger.info("  ✓ Imagem processada: %d frames", len(results))
                    except Exception as ex_img:  # pylint: disable=broad-exception-caught
                        logger.warning(
                            "  ⚠️ model() falhou para imagem: %s. "
                            "Tentando via track() e fallback frame-a-frame",
                            ex_img
                        )
                        try:
                            results = list(model.track(
                                source=tmp_path,
                                device=settings.INFERENCE_DEVICE,
                                verbose=False,
                                persist=True,
                                stream=True,  # Evita acumular na RAM
                                vid_stride=max(1, settings.VIDEO_INFERENCE_STRIDE),
                                conf=settings.DETECTION_CONF_THRESHOLD,
                                iou=settings.DETECTION_IOU_THRESHOLD,
                            ))
                            logger.info(
                                "  ✓ Imagem processada via track fallback: %d frames",
                                len(results)
                            )
                        except Exception as ex_track2:  # pylint: disable=broad-exception-caught
                            logger.warning(
                                "  ⚠️ track() também falhou: %s. Tentando frame-a-frame",
                                ex_track2
                            )
                            results = self._process_video_frames(tmp_path, model)
                            logger.info(
                                "  ✓ Processado frame-a-frame após fallback: %d frames",
                                len(results)
                            )

                if total_frames_processed == 0:
                    total_frames_processed = len(results)

                model_frames_with_det = 0
                max_detections_per_frame = defaultdict(int)

                # Processar resultados deste modelo
                for frame_idx, result in enumerate(results):
                    if not result.boxes or len(result.boxes) == 0:
                        continue

                    model_frames_with_det += 1
                    cls_list = result.boxes.cls.tolist()
                    names = result.names
                    frame_boxes_by_class = defaultdict(list)

                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        class_id = int(box.cls.item())
                        confidence = float(box.conf.item())
                        class_name = names[int(class_id)]
                        track_id = None

                        if result.boxes.id is not None:
                            try:
                                track_id = int(box.id.item())
                            except Exception:  # pylint: disable=broad-exception-caught
                                track_id = None

                        all_detection_boxes.append({
                            "frame_index": frame_idx,
                            "class_id": class_id,
                            "class_name": class_name,
                            "confidence": confidence,
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "track_id": track_id,
                            "model_source": current_model_name
                        })

                        frame_boxes_by_class[class_name].append({
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "confidence": confidence,
                        })

                    if result.boxes.id is not None:
                        for t_id, c_id in zip(result.boxes.id.tolist(), cls_list):
                            global_unique_objects[names[int(c_id)]].add(int(t_id))

                    for class_name, frame_boxes in frame_boxes_by_class.items():
                        deduped_boxes = self._deduplicate_boxes_by_iou(
                            frame_boxes,
                            settings.COUNT_DEDUP_IOU_THRESHOLD,
                        )
                        max_detections_per_frame[class_name] = max(
                            max_detections_per_frame[class_name],
                            len(deduped_boxes),
                        )

                global_frames_with_detections = max(
                    global_frames_with_detections, model_frames_with_det
                )

                # Agregar ao global_class_counts
                for name, cnt in max_detections_per_frame.items():
                    global_class_counts[name] = max(global_class_counts[name], cnt)

            # Consolidar contagens finais
            final_counts = {}
            for name, cnt in global_class_counts.items():
                final_counts[name] = cnt

            if not is_video:
                for name, ids in global_unique_objects.items():
                    final_counts[name] = max(final_counts.get(name, 0), len(ids))

            # Se nenhuma detecção foi feita
            if not final_counts:
                final_counts = {}
                logger.warning("⚠️ Nenhuma detecção encontrada na cena")

            logger.info("✓ Detecção global concluída: %s", final_counts)

            # Desenhar detecções no arquivo e salvar
            # Passamos all_detection_boxes para o draw
            analyzed_file_path = await self._draw_and_save_results(
                tmp_path, all_detection_boxes, file.filename, is_video
            )
            analyzed_filename = Path(analyzed_file_path).name
            analyzed_output = {
                "path": analyzed_file_path,
                "filename": analyzed_filename,
                "download_url": f"/detection/download/{analyzed_filename}",
            }

            return {
                "requested_model": requested_model,
                "class_counts": final_counts,
                "num_frames_processed": total_frames_processed,
                "frames_with_detections": global_frames_with_detections,
                "analyzed_file": analyzed_file_path,
                "analyzed_output": analyzed_output,
                "boxes": all_detection_boxes,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("❌ Erro na detecção: %s", error_msg, exc_info=True)
            raise Exception(f"Erro na detecção: {error_msg}") from e

        finally:
            # Limpar arquivos temporários
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception as cleanup_err:  # pylint: disable=broad-exception-caught
                logger.warning("⚠️ Erro ao limpar: %s", cleanup_err)

    def _process_video_frames(self, video_path: str, model) -> list:
        """Processes a video frame by frame as a fallback to tracking."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

        frame_results = []
        frame_idx = 0

        while True:
            success, frame = cap.read()
            if not success:
                break

            frame_idx += 1
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = model(
                rgb_frame,
                device=settings.INFERENCE_DEVICE,
                conf=settings.DETECTION_CONF_THRESHOLD,
                iou=settings.DETECTION_IOU_THRESHOLD,
            )

            if results:
                frame_results.extend(results)

            if frame_idx % 100 == 0:
                logger.info("⌛ Vídeo (frame-a-frame): processados %d frames", frame_idx)

        cap.release()
        return frame_results

    @staticmethod
    def _safe_stem(filename: str) -> str:
        """Sanitizes filename stems for use in paths."""
        stem = Path(filename).stem if filename else "upload"
        sanitized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem)
        return sanitized or "upload"

    def _save_training_artifacts(
        self, content: bytes, original_filename: str, suffix: str, is_video: bool
    ):
        """Saves incoming uploads as training artifacts."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_stem = self._safe_stem(original_filename)
        ext = suffix if suffix else ".bin"
        saved_name = f"{safe_stem}_{timestamp}{ext}"

        if is_video:
            saved_video_path = self.training_uploads_videos_dir / saved_name
            with open(saved_video_path, "wb") as f:
                f.write(content)

            frames_session_dir = self.training_video_frames_dir / f"{safe_stem}_{timestamp}"
            frames_saved = self._extract_all_video_frames(saved_video_path, frames_session_dir)
            logger.info(
                "🧠 Artefatos de treino salvos (video): %s | frames=%d",
                saved_video_path,
                frames_saved,
            )
            return

        saved_image_path = self.training_uploads_images_dir / saved_name
        with open(saved_image_path, "wb") as f:
            f.write(content)

        logger.info("🧠 Artefato de treino salvo (imagem): %s", saved_image_path)

    @staticmethod
    def _extract_all_video_frames(video_path: Path, output_frames_dir: Path) -> int:
        """Extracts and saves all frames from a video file."""
        output_frames_dir.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise IOError(f"Não foi possível abrir vídeo para extração de frames: {video_path}")

        frame_idx = 0
        while True:
            success, frame = cap.read()
            if not success:
                break

            frame_file = output_frames_dir / f"frame_{frame_idx:06d}.jpg"
            cv2.imwrite(str(frame_file), frame)
            frame_idx += 1

        cap.release()
        return frame_idx

    @staticmethod
    def _calculate_iou(box_a: dict, box_b: dict) -> float:
        """Calcula IoU entre duas boxes no formato {x1,y1,x2,y2}."""
        x_left = max(box_a["x1"], box_b["x1"])
        y_top = max(box_a["y1"], box_b["y1"])
        x_right = min(box_a["x2"], box_b["x2"])
        y_bottom = min(box_a["y2"], box_b["y2"])

        if x_right <= x_left or y_bottom <= y_top:
            return 0.0

        intersection = (x_right - x_left) * (y_bottom - y_top)
        area_a = max(0, box_a["x2"] - box_a["x1"]) * max(0, box_a["y2"] - box_a["y1"])
        area_b = max(0, box_b["x2"] - box_b["x1"]) * max(0, box_b["y2"] - box_b["y1"])

        union = area_a + area_b - intersection
        if union <= 0:
            return 0.0

        return intersection / union

    def _deduplicate_boxes_by_iou(self, boxes: list, iou_threshold: float) -> list:
        """Deduplica boxes sobrepostas mantendo as de maior confiança."""
        if not boxes:
            return []

        sorted_boxes = sorted(boxes, key=lambda b: b.get("confidence", 0.0), reverse=True)
        kept = []

        for candidate in sorted_boxes:
            is_duplicate = False
            for accepted in kept:
                if self._calculate_iou(candidate, accepted) >= iou_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                kept.append(candidate)

        return kept

    async def _draw_and_save_results(
        self, source_path: str, detection_boxes: list, original_filename: str, is_video: bool
    ) -> str:
        """Desenha as detecções no arquivo e salva."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(original_filename).suffix.lower()

        # Correção: Se a imagem original era webp ou jpg, mas virou vídeo na simulação, forçamos o .mp4
        if is_video and file_ext not in [".mp4", ".mov", ".avi", ".mkv"]:
            file_ext = ".mp4"

        output_filename = f"analyzed_{Path(original_filename).stem}_{timestamp}{file_ext}"
        output_path = self.output_dir / output_filename

        if is_video:
            return await self._draw_and_save_video(source_path, detection_boxes, output_path)
        return await self._draw_and_save_image(source_path, detection_boxes, output_path)

    async def _draw_and_save_image(
        self, image_path: str, detection_boxes: list, output_path: Path
    ) -> str:
        """Desenha detecções em uma imagem e salva."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Não foi possível ler a imagem: {image_path}")

            # Desenhar todas as boxes agregadas
            for box in detection_boxes:
                x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
                class_name = box["class_name"]
                conf = box["confidence"]

                # Desenhar retângulo
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Desenhar texto com classe e confiança
                label = f"{class_name} {conf:.2%}"
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(
                    img, (x1, y1 - text_size[1] - 4), (x1 + text_size[0], y1), (0, 255, 0), -1
                )
                cv2.putText(img, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            # Salvar imagem
            cv2.imwrite(str(output_path), img)
            logger.info("✅ Imagem analisada salva: %s", output_path)
            return str(output_path)
        except Exception as e:
            logger.error("❌ Erro ao salvar imagem analisada: %s", e)
            raise

    async def _draw_and_save_video(
        self, video_path: str, detection_boxes: list, output_path: Path
    ) -> str:
        """Desenha detecções em um vídeo e salva."""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

            # Obter propriedades do vídeo
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Configurar codec e writer
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            output_video = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

            if not output_video.isOpened():
                cap.release()
                raise IOError(f"Não foi possível criar arquivo de vídeo: {output_path}")

            # Agrupar boxes por frame
            boxes_by_frame = defaultdict(list)
            for box in detection_boxes:
                boxes_by_frame[box["frame_index"]].append(box)

            frame_idx = 0

            while True:
                success, frame = cap.read()
                if not success:
                    break

                # Desenhar detecções se houver resultado para este frame
                if frame_idx in boxes_by_frame:
                    for box in boxes_by_frame[frame_idx]:
                        x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
                        class_name = box["class_name"]
                        conf = box["confidence"]

                        # Desenhar retângulo
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                        # Desenhar texto com classe e confiança
                        label = f"{class_name} {conf:.2%}"
                        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                        cv2.rectangle(
                            frame,
                            (x1, y1 - text_size[1] - 4),
                            (x1 + text_size[0], y1),
                            (0, 255, 0),
                            -1
                        )
                        cv2.putText(
                            frame, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2
                        )

                output_video.write(frame)
                frame_idx += 1

                if frame_idx % 100 == 0:
                    logger.info("⌛ Vídeo: salvos %d/%d frames", frame_idx, total_frames)

            cap.release()
            output_video.release()
            logger.info("✅ Vídeo analisado salva: %s", output_path)
            return str(output_path)
        except Exception as e:
            logger.error("❌ Erro ao salvar vídeo analisado: %s", e)
            raise

    # pylint: disable=too-many-return-statements
    @staticmethod
    def _detect_file_type_from_bytes(header: bytes) -> str:
        """Detecta tipo de arquivo usando magic bytes (primeiros bytes do arquivo)"""
        if len(header) < 4:
            return "Desconhecido"

        # Assinaturas de arquivo
        signatures = {
            (b'\xFF\xD8\xFF', 3): "JPEG",
            (b'\x89PNG\r\n\x1a\n', 8): "PNG",
            (b'GIF87a', 6): "GIF87",
            (b'GIF89a', 6): "GIF89",
            (b'\x1A\x45\xDF\xA3', 4): "MKV",
            (b'\x00\x00\x00\x14ftyp', 12): "MP4/MOV",
            (b'\x00\x00\x00\x18ftyp', 12): "MP4/MOV",
            (b'\x00\x00\x00\x20ftyp', 12): "MP4/MOV",
        }

        for sig, min_len in signatures:
            if len(header) >= min_len and header.startswith(sig):
                return signatures[(sig, min_len)]

        # Detectar MP4/MOV com ftyp em offset 4 (variações de boxes)
        if len(header) >= 12 and header[4:8] == b"ftyp":
            return "MP4/MOV"

        # Detectar AVI and WEBP baseados no container RIFF
        if len(header) >= 12 and header.startswith(b"RIFF"):
            if header[8:12] == b"AVI ":
                return "AVI/WAV"
            if header[8:12] == b"WEBP":
                return "WEBP"

        # Abertura de MKV / WebM (EBML)
        if len(header) >= 4 and header.startswith(b"\x1A\x45\xDF\xA3"):
            return "MKV"

        return f"Desconhecido (header: {header[:8].hex()})"