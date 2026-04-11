from ultralytics import YOLO
from collections import defaultdict
import os
import tempfile
from fastapi import UploadFile
from config.settings import settings
import logging
import cv2
from pathlib import Path
import numpy as np
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class DetectionService:
    def __init__(self):
        # Caminho absoluto para o diretório de modelos
        self.models_dir = Path(__file__).parent.parent.parent.parent / "models"
        # Diretório para salvar arquivos analisados
        self.output_dir = Path(__file__).parent.parent.parent.parent / "analyzed_outputs"
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
        print(f"✅ Serviço de detecção inicializado!")

    def get_model(self, model_name: str = None):
        """Carrega ou retorna modelo do cache."""
        if model_name is None:
            model_name = "chair"  # Modelo padrão

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
            raise ValueError(f"Erro ao carregar modelo '{model_name}': {e}")

    @staticmethod
    def _validate_model_name(model_name: str) -> str:
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Nome de modelo invalido")

        clean_name = model_name.strip()
        if len(clean_name) > 64:
            raise ValueError("Nome de modelo invalido: muito longo")

        # Permite apenas nomes seguros para evitar path traversal e caracteres especiais.
        if not re.fullmatch(r"[A-Za-z0-9_-]+", clean_name):
            raise ValueError("Nome de modelo invalido: use apenas letras, numeros, _ e -")

        return clean_name

    def list_available_models(self):
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
        selected_model = self._validate_model_name(model_name or "chair")

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
            
        supported_formats = [".bmp",".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi", ".mkv", ".gif", ".webp"]
        
        if suffix not in supported_formats:
            raise ValueError(f"Formato não suportado: {suffix}. Use: {', '.join(supported_formats)}")

        # Criar diretório temporário
        temp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(temp_dir, f"upload{suffix}")
        
        try:
            # Ler arquivo
            content = await file.read()
            if not content:
                raise ValueError("Arquivo vazio recebido")
            
            # Verificar tamanho (máx 500 MB)
            file_size_mb = len(content) / (1024 * 1024)
            if file_size_mb > 500:
                raise ValueError(f"Arquivo muito grande: {file_size_mb:.1f} MB (máx: 500 MB)")
            
            # Salvar arquivo
            with open(tmp_path, "wb") as f:
                f.write(content)
            
            logger.info(f"✓ Arquivo salvo: {tmp_path} ({file_size_mb:.1f} MB)")
            
            # Carregar modelo selecionado
            model = self.get_model(selected_model)
            logger.info(f"🤖 Usando modelo: {selected_model}")
            
            # Detectar tipo real usando magic bytes
            file_type = self._detect_file_type_from_bytes(content[:20])
            logger.info(f"✓ Tipo detectado: {file_type}")
            logger.info(
                "⚙️ Thresholds: conf=%.2f iou=%.2f dedup_iou=%.2f",
                settings.DETECTION_CONF_THRESHOLD,
                settings.DETECTION_IOU_THRESHOLD,
                settings.COUNT_DEDUP_IOU_THRESHOLD,
            )

            # Decidir se é vídeo por extensão e/ou magic bytes
            video_extensions = [".mp4", ".mov", ".avi", ".mkv"]
            image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
            is_video = suffix in video_extensions or file_type in ["MP4/MOV", "AVI/WAV", "MKV"]
            is_image = suffix in image_extensions or file_type in ["JPEG", "PNG", "GIF87", "GIF89"]

            # Salvar sempre os arquivos recebidos para possível reuso em treino.
            if settings.SAVE_TRAINING_ARTIFACTS:
                self._save_training_artifacts(content, file.filename, suffix, is_video)

            # Avisar se arquivo é grande
            if file_size_mb > 100:
                logger.warning(f"⚠️ Arquivo grande ({file_size_mb:.1f} MB) - processamento pode ser lento")

            logger.info(f"🔍 Iniciando detecção... (is_video={is_video}, is_image={is_image})")

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
                logger.info(f"✓ Duração do vídeo: {duration_sec:.1f}s")

            # Suporta imagem e vídeo; para vídeo, tentamos track + fallback frame-by-frame
            if is_video:
                try:
                    results = list(model.track(
                        source=tmp_path,
                        device=settings.INFERENCE_DEVICE,
                        verbose=False,
                        persist=True,
                        stream=True,  # Evita acumular na RAM
                        conf=settings.DETECTION_CONF_THRESHOLD,
                        iou=settings.DETECTION_IOU_THRESHOLD,
                    ))
                    logger.info(f"✓ Vídeo processado via track: {len(results)} frames")
                except Exception as ex_track:
                    logger.warning(f"⚠️ track() falhou para vídeo: {ex_track}. Tentando frame-a-frame")
                    results = self._process_video_frames(tmp_path, model)
                    logger.info(f"✓ Vídeo processado frame-a-frame: {len(results)} frames")
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
                    logger.info(f"✓ Imagem processada: {len(results)} frames")
                except Exception as ex_img:
                    logger.warning(f"⚠️ model() falhou para imagem: {ex_img}. Tentando via track() e fallback frame-a-frame")
                    try:
                        results = list(model.track(
                            source=tmp_path,
                            device=settings.INFERENCE_DEVICE,
                            verbose=False,
                            persist=True,
                            stream=True,  # Evita acumular na RAM
                            conf=settings.DETECTION_CONF_THRESHOLD,
                            iou=settings.DETECTION_IOU_THRESHOLD,
                        ))
                        logger.info(f"✓ Imagem/vídeo processado via track fallback: {len(results)} frames")
                    except Exception as ex_track2:
                        logger.warning(f"⚠️ track() também falhou: {ex_track2}. Tentando frame-a-frame")
                        results = self._process_video_frames(tmp_path, model)
                        logger.info(f"✓ Processado frame-a-frame após fallback: {len(results)} frames")


            unique_objects = defaultdict(set)
            max_detections_per_frame = defaultdict(int)
            total_frames_with_detections = 0
            detection_boxes = []

            # Processar resultados
            for frame_idx, result in enumerate(results):
                # Verificar se há boxes neste frame
                if not result.boxes or len(result.boxes) == 0:
                    logger.debug(f"  Frame {frame_idx}: nenhuma detecção")
                    continue
                
                total_frames_with_detections += 1
                cls_list = result.boxes.cls.tolist()
                names = result.names
                frame_boxes_by_class = defaultdict(list)

                # Exportar boxes detectadas para o retorno da API
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    class_id = int(box.cls.item())
                    confidence = float(box.conf.item())
                    class_name = names[int(class_id)]
                    track_id = None

                    if result.boxes.id is not None:
                        try:
                            track_id = int(box.id.item())
                        except Exception:
                            track_id = None

                    detection_boxes.append({
                        "frame_index": frame_idx,
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": confidence,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "track_id": track_id,
                    })

                    frame_boxes_by_class[class_name].append({
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "confidence": confidence,
                    })
                
                # Debug: mostrar o mapeamento exato das classes
                cls_names = [names[int(c_id)] for c_id in cls_list]
                logger.debug(f"  Frame {frame_idx}: {len(cls_list)} detecções -> {cls_names}")

                if result.boxes.id is not None:
                    for t_id, c_id in zip(result.boxes.id.tolist(), cls_list):
                        unique_objects[names[int(c_id)]].add(int(t_id))

                # Sempre calcula o pico por frame (deduplicado por IoU),
                # para reduzir supercontagem causada por troca de track_id no vídeo.
                for class_name, frame_boxes in frame_boxes_by_class.items():
                    deduped_boxes = self._deduplicate_boxes_by_iou(
                        frame_boxes,
                        settings.COUNT_DEDUP_IOU_THRESHOLD,
                    )
                    max_detections_per_frame[class_name] = max(
                        max_detections_per_frame[class_name],
                        len(deduped_boxes),
                    )

            # Consolidar resultados
            final_counts = {}
            
            # Para vídeo, usar o pico por frame deduplicado para evitar inflação por id-switch.
            # Para imagem, mantém o comportamento existente (rastreamento quando disponível).
            for name, cnt in max_detections_per_frame.items():
                final_counts[name] = cnt

            if not is_video:
                for name, ids in unique_objects.items():
                    final_counts[name] = max(final_counts.get(name, 0), len(ids))
            
            # Se nenhuma detecção foi feita, retornar vazio mas válido
            if not final_counts:
                final_counts = {}
                logger.warning(f"⚠️ Nenhuma detecção encontrada na cena")
            
            logger.info(f"✓ Detecção concluída: {final_counts}")
            logger.info(f"  Frames com detecção: {total_frames_with_detections}/{len(results)}")

            # Desenhar detecções no arquivo e salvar
            analyzed_file_path = await self._draw_and_save_results(
                tmp_path, results, model, file.filename, is_video
            )
            analyzed_filename = Path(analyzed_file_path).name
            analyzed_output = {
                "path": analyzed_file_path,
                "filename": analyzed_filename,
                "download_url": f"/detection/download/{analyzed_filename}",
            }

            return {
                "analysis_model_used": selected_model,
                "class_counts": final_counts,
                "num_frames_processed": len(results),
                "detected_chairs": final_counts.get("chair", 0),
                "frames_with_detections": total_frames_with_detections,
                "message": "Nenhuma cadeira detectada" if final_counts.get("chair", 0) == 0 else f"{final_counts.get('chair', 0)} cadeira(s) detectada(s)",
                "analyzed_file": analyzed_file_path,
                "analyzed_output": analyzed_output,
                "boxes": detection_boxes,
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Erro na detecção: {error_msg}", exc_info=True)
            raise Exception(f"Erro na detecção: {error_msg}")
            
        finally:
            # Limpar arquivos temporários
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as cleanup_err:
                logger.warning(f"⚠️ Erro ao limpar: {cleanup_err}")

    def _process_video_frames(self, video_path: str, model):
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
                logger.info(f"⌛ Vídeo (frame-a-frame): processados {frame_idx} frames")

        cap.release()
        return frame_results

    @staticmethod
    def _safe_stem(filename: str) -> str:
        stem = Path(filename).stem if filename else "upload"
        sanitized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem)
        return sanitized or "upload"

    def _save_training_artifacts(self, content: bytes, original_filename: str, suffix: str, is_video: bool):
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

    async def _draw_and_save_results(self, source_path: str, results, model, original_filename: str, is_video: bool):
        """Desenha as detecções no arquivo e salva."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(original_filename).suffix.lower()
        output_filename = f"analyzed_{Path(original_filename).stem}_{timestamp}{file_ext}"
        output_path = self.output_dir / output_filename

        if is_video:
            return await self._draw_and_save_video(source_path, results, model, output_path)
        else:
            return await self._draw_and_save_image(source_path, results, model, output_path)

    async def _draw_and_save_image(self, image_path: str, results, model, output_path: Path):
        """Desenha detecções em uma imagem e salva."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Não foi possível ler a imagem: {image_path}")

            # Processar primeiro resultado (uma imagem = um resultado)
            if results and len(results) > 0:
                result = results[0]
                if result.boxes:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls = int(box.cls.item())
                        conf = box.conf.item()
                        class_name = model.names.get(cls, f"Classe {cls}")

                        # Desenhar retângulo
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

                        # Desenhar texto com classe e confiança
                        label = f"{class_name} {conf:.2%}"
                        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                        cv2.rectangle(img, (x1, y1 - text_size[1] - 4), (x1 + text_size[0], y1), (0, 255, 0), -1)
                        cv2.putText(img, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            # Salvar imagem
            cv2.imwrite(str(output_path), img)
            logger.info(f"✅ Imagem analisada salva: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar imagem analisada: {e}")
            raise

    async def _draw_and_save_video(self, video_path: str, results, model, output_path: Path):
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
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            output_video = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

            if not output_video.isOpened():
                cap.release()
                raise IOError(f"Não foi possível criar arquivo de vídeo: {output_path}")

            frame_idx = 0
            result_idx = 0

            while True:
                success, frame = cap.read()
                if not success:
                    break

                # Desenhar detecções se houver resultado para este frame
                if result_idx < len(results):
                    result = results[result_idx]
                    if result.boxes:
                        for box in result.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cls = int(box.cls.item())
                            conf = box.conf.item()
                            class_name = model.names.get(cls, f"Classe {cls}")

                            # Desenhar retângulo
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                            # Desenhar texto com classe e confiança
                            label = f"{class_name} {conf:.2%}"
                            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                            cv2.rectangle(frame, (x1, y1 - text_size[1] - 4), (x1 + text_size[0], y1), (0, 255, 0), -1)
                            cv2.putText(frame, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                    result_idx += 1

                output_video.write(frame)
                frame_idx += 1

                if frame_idx % 100 == 0:
                    logger.info(f"⌛ Vídeo: salvos {frame_idx}/{total_frames} frames")

            cap.release()
            output_video.release()
            logger.info(f"✅ Vídeo analisado salvo: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar vídeo analisado: {e}")
            raise

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
            (b'RIFF', 4): "AVI/WAV",
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

        # Detectar AVI com RIFF + AVI
        if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"AVI ":
            return "AVI/WAV"

        # Abertura de MKV / WebM (EBML)
        if len(header) >= 4 and header.startswith(b"\x1A\x45\xDF\xA3"):
            return "MKV"

        return f"Desconhecido (header: {header[:8].hex()})"