"""
Detection service module.
Manages loading YOLO models, caching them, running inference on images and videos,
deduplicating bounding boxes, drawing detection results, and saving training artifacts.
"""
# pylint: disable=too-many-instance-attributes, too-many-locals, too-many-branches, too-many-statements
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

import cv2
from fastapi import UploadFile
from ultralytics import YOLO

from app.services.compliance_service import compliance_service
from app.utils.test_simulator import simulate_video_from_image
from app.utils.translations import translate_class_name
from config.settings import settings

logger = logging.getLogger(__name__)

# Mapeamento de nomes compactos para os nomes longos das pastas físicas no disco
MODEL_ALIASES = {
    "alimentos e utensílios": "apple_bag_bag_noodles_banana_garrafa_bowl_noodles_etc",
    "queda e epi": "caiu_luvas_culos_de_proteo_capuz_de_segurana_etc",
    "caixas e pessoas": "caixa_continer_escada_de_palhasa_pessoa",
    "caixas e pacotes": "caixa_fechada_caixa_aberta_pacotes",
    "extintor co2 e sílica": "co2_porttil_mc_2a_co2_mf_60_slica_ya_10nx",
    "cones de segurança": "cono_de_segurana",
    "óculos de proteção": "culos_sem_culos",
    "vagas de estacionamento": "espao_vazio_espao_ocupado",
    "escavadeira e carros": "excavador_carro_carro_2",
    "frascos e garrafas": "frasco_de_vidro_castanho_frasco_de_vidro_limpo_etc",
    "etiquetas e caixas": "fundo_caixas_etiquetas",
    "máquinas e obras": "mixer_esgoto_caminho_esgoto_escavadeira",
    "ônibus e caminhões": "nibus_grande_caminho_grande_nibus_longo_nibus_etc",
    "coletes de segurança": "sem_veste_de_segurana_veste_de_segurana",
    "máquinas pesadas": "zuado_caminho_burro_escavadeira_chamin_carro_etc",
    "carros variados": "carro_carro_2",
    "sinal de parque": "sinal_de_parque",
    "sínal de parque": "sinal_de_parque",
    "item caixa": "item_caixa",
    "extintor e sua sinalização": "extinguidor",
    "cadeira": "cadeira",
    "caminho": "caminho",
    "carro": "carro",
    "pessoa": "pessoa"
}

REVERSE_MODEL_ALIASES = {v: k for k, v in MODEL_ALIASES.items()}

# Modelos desativados (não relevantes para construção civil/segurança/governamental)
DISABLED_MODELS = {
    "alimentos e utensílios",
    "frascos e garrafas",
    "apple_bag_bag_noodles_banana_garrafa_bowl_noodles_etc",
    "frasco_de_vidro_castanho_frasco_de_vidro_limpo_etc",
}


# Limiares de confiança sugeridos por classe (Média - 1.5*StdDev + 40% da Média)
CLASS_CONFIDENCE_THRESHOLDS = {
    "Arroz": 0.40,
    "Cadeira": 0.40,
    "Caixa": 0.40,
    "Caixa Aberta": 0.48,
    "Caixa Fechada": 0.40,
    "Caixas": 0.40,
    "Caminhão": 0.64,
    "Caminhão Betoneira": 0.43,
    "Caminhão Caçamba": 0.40,
    "Caminhão Grande": 0.40,
    "Caminhão Médio": 0.42,
    "Caminhão Pequeno": 0.40,
    "Capacete de Segurança": 0.40,
    "Carregadeira": 0.40,
    "Carro": 0.40,
    "Caçamba": 0.40,
    "Colete de Segurança": 0.40,
    "Cone de Segurança": 0.40,
    "Contêiner": 0.40,
    "Empilhadeira": 0.48,
    "Escavadeira": 0.40,
    "Etiquetas": 0.40,
    "Extintor CO2 Babcock Davis": 0.46,
    "Extintor CO2 Walker MC-2A": 0.40,
    "Extintor Espuma Walker MF-60": 0.40,
    "Extintor Yamato YA-10NX": 0.40,
    "Extintor de Incêndio": 0.40,
    "Garrafa de Vidro Transparente": 0.56,
    "Guindaste Móvel": 0.40,
    "Lata": 0.61,
    "Lata de Doce": 0.51,
    "Melão": 0.48,
    "Miojo de Pacote": 0.51,
    "Motoniveladora": 0.40,
    "Máscara": 0.88,
    "Neve": 0.46,
    "Pacotes": 0.40,
    "Pessoa": 0.40,
    "Placa de Veículo": 0.40,
    "Produto": 0.45,
    "Queda Detectada": 0.40,
    "Rolinho Primavera": 0.54,
    "Rolo Compressor": 0.49,
    "Sem Colete de Segurança": 0.54,
    "Sem Máscara": 0.40,
    "Sem Óculos de Proteção": 0.46,
    "Shoutao": 0.52,
    "Trator de Esteira (Bulldozer)": 0.45,
    "Vaga Ocupada": 0.40,
    "Vaga Vazia": 0.40,
    "Ônibus Grande": 0.66,
}



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

        self.jobs = {}  # Gerenciador de Jobs assíncronos
        self.request_id_to_job_id = {}  # Cache de request_id -> job_id para idempotência
        self.executor = ThreadPoolExecutor(max_workers=settings.DETECTION_MAX_WORKERS)  # Thread pool global compartilhado
        self._model_load_lock = threading.Lock()  # Lock para carregamento concorrente seguro de modelos
        self._model_locks = {}  # Lock por modelo para inferência concorrente segura
        
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

        # Resolve aliases para a pasta física correspondente
        physical_name = MODEL_ALIASES.get(model_name, model_name)
        physical_name = self._validate_model_name(physical_name)

        if physical_name in self.models_cache:
            return self.models_cache[physical_name]

        # Sincroniza o carregamento do disco/compilação OpenVINO para evitar deadlocks de concorrência
        with self._model_load_lock:
            # Checagem dupla após adquirir a trava
            if physical_name in self.models_cache:
                return self.models_cache[physical_name]

            # Procurar modelo na pasta correspondente
            model_folder = self.models_dir / physical_name
            if not model_folder.exists():
                raise ValueError(f"Modelo '{model_name}' não encontrado em {model_folder}")

            # Procurar pasta openvino primeiro para aceleração de hardware Intel
            openvino_folders = list(model_folder.glob("*_openvino_model"))
            if openvino_folders:
                model_path = openvino_folders[0]
                print(f"🔄 Carregando modelo no formato OpenVINO: {model_path}")
            else:
                # Procurar arquivo .pt
                pt_files = list(model_folder.glob("*.pt"))
                if not pt_files:
                    raise ValueError(f"Nenhum arquivo .pt ou pasta OpenVINO encontrado em {model_folder}")
                model_path = pt_files[0]  # Usar o primeiro encontrado
                print(f"🔄 Carregando modelo (PyTorch): {model_path}")

            try:
                model = YOLO(str(model_path), task="detect")
                self.models_cache[physical_name] = model
                print(f"✅ Modelo '{model_name}' carregado! Classes: {model.names} (Tarefa: {model.task})")
                return model
            except Exception as e:
                raise ValueError(f"Erro ao carregar modelo '{model_name}': {e}") from e

    def preload_all_models(self) -> int:
        """Pré-carrega todos os modelos disponíveis na memória para inicialização instantânea da API."""
        print("⚡ [WARM-UP] Pré-carregando modelos YOLO na memória durante a inicialização...")
        loaded_count = 0
        for model_name in self.available_models:
            try:
                self.get_model(model_name)
                loaded_count += 1
            except Exception as e:
                logger.warning("⚠️ Falha ao pré-carregar o modelo '%s': %s", model_name, e)
        print(f"🚀 [WARM-UP] Concluído! {loaded_count}/{len(self.available_models)} modelos prontos em memória.")
        return loaded_count

    @staticmethod
    def _validate_model_name(model_name: str) -> str:
        """Validates that a model name is clean and safe from path traversal."""
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Nome de modelo invalido")

        clean_name = model_name.strip()
        if len(clean_name) > 64:
            raise ValueError("Nome de modelo invalido: muito longo")

        # Permite letras, números, espaços, underscores, hífens e acentos comuns em português.
        if not re.fullmatch(r"[A-Za-z0-9_ -áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]+", clean_name):
            raise ValueError("Nome de modelo inválido: use apenas letras, números, espaços, acentos comuns e -_")

        return clean_name

    def _get_model_inference_lock(self, physical_name: str) -> threading.Lock:
        """Retorna uma trava por modelo para garantir thread-safety na inferência do mesmo modelo."""
        with self._model_load_lock:
            if physical_name not in self._model_locks:
                self._model_locks[physical_name] = threading.Lock()
            return self._model_locks[physical_name]

    def _run_single_model_inference(
        self,
        model_name: str,
        source: Any,
        is_video: bool,
        conf_override: Optional[float] = None,
        imgsz_override: Optional[int] = None,
    ) -> List[Any]:
        """Executa a inferência de um único modelo (síncrono, roda dentro do ThreadPoolExecutor)."""
        model = self.get_model(model_name)

        # Definir limiar específico por modelo para evitar falsos positivos
        physical_name = MODEL_ALIASES.get(model_name, model_name)
        if conf_override is not None:
            conf_val = conf_override
        else:
            conf_val = 0.40

        img_size = imgsz_override if imgsz_override else settings.DETECTION_IMAGE_SIZE

        # Determinar dispositivo específico (OpenVINO roda em GPU se disponível; PyTorch .pt roda em CPU)
        is_openvino = False
        model_folder = self.models_dir / physical_name
        if list(model_folder.glob("*_openvino_model")):
            is_openvino = True

        # Para modelos OpenVINO IR compilados com shape estático 640, usa 640 obrigatoriamente
        if is_openvino:
            img_size = 640
        else:
            img_size = imgsz_override if imgsz_override else 640

        device = "intel:gpu" if (is_openvino and settings.INFERENCE_DEVICE == "GPU") else "cpu"

        # Sincronizar inferência por modelo para garantir thread-safety no OpenCV/OpenVINO/YOLO
        lock = self._get_model_inference_lock(physical_name)
        with lock:
            # Força o overrides do Ultralytics e zera o cache do predictor com tamanho 1280
            model.overrides["imgsz"] = img_size
            if hasattr(model, "predictor") and model.predictor is not None:
                model.predictor.args.imgsz = img_size

            # Suporta imagem e vídeo; para vídeo, tentamos track + fallback frame-by-frame
            if is_video:
                try:
                    results = list(model.track(
                        source=source,
                        device=device,
                        verbose=False,
                        persist=True,
                        stream=True,  # Evita acumular na RAM
                        vid_stride=max(1, settings.VIDEO_INFERENCE_STRIDE),
                        conf=conf_val,
                        iou=settings.DETECTION_IOU_THRESHOLD,
                        imgsz=img_size,
                    ))
                    return results
                except Exception as ex_track:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "  ⚠️ track() falhou para vídeo (%s): %s. Tentando frame-a-frame",
                        model_name,
                        ex_track
                    )
                    if isinstance(source, (str, Path)):
                        results = self._process_video_frames(source, model)
                        return results
                    return []
            else:
                try:
                    results = list(model(
                        source,
                        device=device,
                        verbose=False,
                        stream=True,  # Evita acumular na RAM
                        conf=conf_val,
                        iou=settings.DETECTION_IOU_THRESHOLD,
                        imgsz=img_size,
                    ))
                    return results
                except Exception as ex_img:  # pylint: disable=broad-exception-caught
                    logger.warning("  ⚠️ model() falhou para imagem (%s): %s", model_name, ex_img)
                    return []

    def list_available_models(self) -> List[str]:
        """Lista modelos disponíveis."""
        if not self.models_dir.exists():
            return []

        models = []
        for folder in self.models_dir.iterdir():
            if folder.is_dir() and not folder.name.startswith('.'):
                pt_files = list(folder.glob("*.pt"))
                openvino_folders = list(folder.glob("*_openvino_model"))
                # Se tiver .pt OU se tiver pasta OpenVINO, considera disponível
                if pt_files or openvino_folders:
                    # Usa o alias compacto se existir para exibição limpa
                    alias_name = REVERSE_MODEL_ALIASES.get(folder.name, folder.name)
                    if alias_name in DISABLED_MODELS or folder.name in DISABLED_MODELS:
                        continue
                    models.append(alias_name)
        return sorted(models)

    @property
    def semaphore(self) -> Optional[asyncio.Semaphore]:
        """Inicializa o semáforo de concorrência de forma tardia (lazy)."""
        if not hasattr(self, "_semaphore"):
            try:
                # Tenta obter o loop de eventos atual para associar o semáforo
                asyncio.get_running_loop()
                self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_INFERENCES)
            except RuntimeError:
                # Retorna None caso não exista loop de eventos ativo
                return None
        return self._semaphore

    async def analyze(self, file: UploadFile, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Analisa um arquivo fazendo uso do semáforo de concorrência."""
        if self.semaphore:
            async with self.semaphore:
                return await self._analyze_internal(file, model_name)
        else:
            return await self._analyze_internal(file, model_name)

    async def _analyze_internal(self, file: UploadFile, model_name: Optional[str] = None) -> Dict[str, Any]:
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

            # Executar apenas o modelo solicitado para evitar desperdício de GPU e gargalos de concorrência.
            # Caso "all" seja enviado, executa a varredura de todos os modelos disponíveis.
            loop = asyncio.get_running_loop()
            models_to_run = []
            if requested_model.lower() == "all":
                models_to_run = self.available_models
            else:
                resolved_alias = REVERSE_MODEL_ALIASES.get(requested_model, requested_model)
                if resolved_alias in self.available_models:
                    models_to_run = [resolved_alias]
                else:
                    default_alias = REVERSE_MODEL_ALIASES.get(self.default_model, self.default_model)
                    models_to_run = [default_alias]

            logger.info("⚡ Executando inferência para os modelos: %s", models_to_run)

            tasks = [
                loop.run_in_executor(
                    self.executor,
                    self._run_single_model_inference,
                    current_model_name,
                    tmp_path,
                    is_video
                )
                for current_model_name in models_to_run
            ]

            # Executa a inferência em paralelo
            models_results = await asyncio.gather(*tasks)

            # Iterar resultados obtidos
            for current_model_name, results in zip(models_to_run, models_results):
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
                        class_name = translate_class_name(names[int(class_id)])

                        # Limiar de confiança individual por classe
                        target_threshold = CLASS_CONFIDENCE_THRESHOLDS.get(
                            class_name, settings.DETECTION_CONF_THRESHOLD
                        )
                        if confidence < target_threshold:
                            continue

                        track_id = None
                        if result.boxes.id is not None and hasattr(box, "id") and box.id is not None:
                            try:
                                track_id = int(box.id.item())
                                global_unique_objects[class_name].add(track_id)
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

            # Obter dimensões reais da mídia para o cálculo de proximidade da conformidade
            img_w, img_h = 1920, 1080
            if is_video:
                cap = cv2.VideoCapture(tmp_path)
                if cap.isOpened():
                    img_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
                    img_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
                cap.release()
            else:
                img_cv = cv2.imread(tmp_path)
                if img_cv is not None:
                    img_h, img_w = img_cv.shape[:2]

            # Rodar motor lógico de conformidade
            compliance_result = compliance_service.evaluate(
                all_detection_boxes, image_width=img_w, image_height=img_h
            )

            # Executar análise em sobcamada (Sub-layer Inspection)
            from app.services.sublayer_service import sub_layer_manager
            sub_layer_results = []
            img_cv_sub = cv2.imread(tmp_path) if (not is_video and os.path.exists(tmp_path)) else None

            for box in all_detection_boxes:
                cname = box.get("class_name")
                roi = None
                if img_cv_sub is not None:
                    x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
                    roi = img_cv_sub[max(0, y1):min(img_h, y2), max(0, x1):min(img_w, x2)]
                res = sub_layer_manager.inspect_cropped_roi(cname, roi, context_boxes=all_detection_boxes)
                if res.get("has_sub_layer"):
                    box["sub_layer"] = res
                    sub_layer_results.append({
                        "object_class": cname,
                        "is_conforming": res["is_conforming"],
                        "passed_items": res["passed_items"],
                        "failed_items": res["failed_items"],
                        "alerts": res["alerts"]
                    })
                    for alert in res["alerts"]:
                        if alert not in compliance_result["alerts"]:
                            compliance_result["alerts"].append(alert)
                            compliance_result["status"] = "NÃO CONFORME"

            # Desenhar detecções no arquivo e salvar (se habilitado)
            analyzed_file_path = None
            analyzed_output = None
            if settings.SAVE_PREDICTION_FILES:
                # Passamos all_detection_boxes para o draw
                analyzed_file_path = await self._draw_and_save_results(
                    tmp_path,
                    all_detection_boxes,
                    file.filename,
                    is_video,
                    compliance_status=compliance_result["status"],
                    compliance_alerts=compliance_result["alerts"]
                )
                analyzed_filename = Path(analyzed_file_path).name
                analyzed_output = {
                    "path": analyzed_file_path,
                    "filename": analyzed_filename,
                    "download_url": f"/detection/download/{analyzed_filename}",
                }

            # Salvar métricas no banco de dados (MySQL/SQLite) em background para evitar latência
            try:
                from app.core.database_metrics import log_prediction
                loop.run_in_executor(
                    self.executor,
                    log_prediction,
                    file.filename,
                    requested_model,
                    final_counts,
                    total_frames_processed,
                    compliance_result["status"],
                    all_detection_boxes
                )
            except Exception as log_err:
                logger.error("⚠️ Erro ao salvar log de métricas no banco: %s", log_err)

            return {
                "requested_model": requested_model,
                "class_counts": final_counts,
                "num_frames_processed": total_frames_processed,
                "frames_with_detections": global_frames_with_detections,
                "analyzed_file": analyzed_file_path,
                "analyzed_output": analyzed_output,
                "boxes": all_detection_boxes,
                "compliance_status": compliance_result["status"],
                "compliance_alerts": compliance_result["alerts"],
                "compliance_report": compliance_result["report"],
                "sub_layer_analysis": sub_layer_results,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("❌ Erro na detecção: %s", error_msg, exc_info=True)
            raise RuntimeError(f"Erro na detecção: {error_msg}") from e

        finally:
            # Limpar arquivos temporários e forçar coleta de lixo
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception as cleanup_err:  # pylint: disable=broad-exception-caught
                logger.warning("⚠️ Erro ao limpar: %s", cleanup_err)
            finally:
                import gc
                gc.collect()

    async def analyze_frame(
        self,
        frame: Any,
        frame_index: int = 0,
        model_name: Optional[str] = None,
        min_confidence: float = 0.25,
        disable_compliance: bool = True,
        imgsz: int = 640,
    ) -> Dict[str, Any]:
        """
        Executa inferência de modelos em um frame (numpy array) na memória.
        Se model_name for fornecido, executa apenas os solicitados (suporta vírgulas: ex 'cadeira,pessoa').
        Pré-redimensiona o quadro uma única vez na memória RAM e escala as coordenadas de volta.
        """
        all_detection_boxes = []
        global_class_counts = defaultdict(int)

        loop = asyncio.get_running_loop()

        # 1. Trata seleção de modelos (suporta modelo único, lista por vírgula ou todos)
        if model_name:
            if "," in model_name:
                requested_list = [m.strip() for m in model_name.split(",") if m.strip()]
                models_to_run = [m for m in requested_list if m in self.available_models]
                if not models_to_run:
                    logger.warning("Nenhum modelo da lista '%s' disponível. Usando todos.", model_name)
                    models_to_run = self.available_models
            elif model_name in self.available_models:
                models_to_run = [model_name]
            else:
                logger.warning("Modelo solicitado '%s' não disponível. Usando todos.", model_name)
                models_to_run = self.available_models
        else:
            models_to_run = self.available_models

        # 2. Pré-redimensionamento único na RAM para 640x640 (exigido pelos modelos OpenVINO IR)
        target_imgsz = 640
        orig_h, orig_w = frame.shape[:2]
        if orig_h != target_imgsz or orig_w != target_imgsz:
            resized_frame = cv2.resize(frame, (target_imgsz, target_imgsz))
        else:
            resized_frame = frame

        scale_x = orig_w / float(target_imgsz)
        scale_y = orig_h / float(target_imgsz)

        tasks = [
            loop.run_in_executor(
                self.executor,
                self._run_single_model_inference,
                current_model_name,
                resized_frame,
                False,
                min_confidence,
                target_imgsz
            )
            for current_model_name in models_to_run
        ]

        all_results = await asyncio.gather(*tasks)

        for current_model_name, results in zip(models_to_run, all_results):
            if not results:
                continue

            max_detections_per_frame = defaultdict(int)

            for result in results:
                if not result.boxes or len(result.boxes) == 0:
                    continue

                names = result.names
                frame_boxes_by_class = defaultdict(list)

                for box in result.boxes:
                    confidence = float(box.conf.item())
                    if confidence < min_confidence:
                        continue

                    x1_raw, y1_raw, x2_raw, y2_raw = map(float, box.xyxy[0])
                    x1 = int(round(x1_raw * scale_x))
                    y1 = int(round(y1_raw * scale_y))
                    x2 = int(round(x2_raw * scale_x))
                    y2 = int(round(y2_raw * scale_y))

                    class_id = int(box.cls.item())
                    class_name = translate_class_name(names[int(class_id)])
                    w_box = max(0, x2 - x1)
                    h_box = max(0, y2 - y1)

                    all_detection_boxes.append({
                        "frame_index": frame_index,
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": round(confidence, 4),
                        "certainty_percent": f"{round(confidence * 100, 2)}%",
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "width": w_box,
                        "height": h_box,
                        "area": w_box * h_box,
                        "track_id": None,
                        "model_source": current_model_name
                    })

                    frame_boxes_by_class[class_name].append({
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "confidence": confidence,
                    })

                for class_name, frame_boxes in frame_boxes_by_class.items():
                    deduped_boxes = self._deduplicate_boxes_by_iou(
                        frame_boxes,
                        settings.COUNT_DEDUP_IOU_THRESHOLD,
                    )
                    max_detections_per_frame[class_name] = max(
                        max_detections_per_frame[class_name],
                        len(deduped_boxes),
                    )

            for class_name, count in max_detections_per_frame.items():
                global_class_counts[class_name] += count

        if disable_compliance:
            compliance_result = {
                "status": "DISABLED",
                "alerts": []
            }
        else:
            h, w = frame.shape[:2]
            compliance_result = compliance_service.evaluate(
                all_detection_boxes, image_width=w, image_height=h
            )

        # Salvar métricas no banco de dados (MySQL/SQLite) em background assíncrono
        try:
            from app.core.database_metrics import log_prediction
            loop.run_in_executor(
                self.executor,
                log_prediction,
                f"stream_frame_{frame_index}",
                model_name or "all",
                dict(global_class_counts),
                1,
                compliance_result["status"],
                all_detection_boxes
            )
        except Exception as log_err:
            logger.error("⚠️ Erro ao registrar métricas da stream: %s", log_err)

        return {
            "class_counts": dict(global_class_counts),
            "boxes": all_detection_boxes,
            "compliance_status": compliance_result["status"],
            "compliance_alerts": compliance_result["alerts"]
        }

    def _process_video_frames(self, video_path: str, model) -> list:
        """Processes a video frame by frame as a fallback to tracking."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Não foi possível abrir o vídeo: {video_path}")

        frame_results = []
        frame_idx = 0

        stride = max(1, settings.VIDEO_INFERENCE_STRIDE)
        while True:
            success, frame = cap.read()
            if not success:
                break

            frame_idx += 1
            if (frame_idx - 1) % stride != 0:
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = model(
                rgb_frame,
                device=settings.INFERENCE_DEVICE,
                conf=settings.DETECTION_CONF_THRESHOLD,
                iou=settings.DETECTION_IOU_THRESHOLD,
                imgsz=settings.DETECTION_IMAGE_SIZE,
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
        self,
        source_path: str,
        detection_boxes: list,
        original_filename: str,
        is_video: bool,
        compliance_status: Optional[str] = None,
        compliance_alerts: Optional[list] = None
    ) -> str:
        """Desenha as detecções no arquivo e salva."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(original_filename).suffix.lower()

        # Correção: Se a imagem original era webp ou jpg, mas virou vídeo na simulação,
        # forçamos o .mp4
        if is_video and file_ext not in [".mp4", ".mov", ".avi", ".mkv"]:
            file_ext = ".mp4"

        output_filename = f"analyzed_{Path(original_filename).stem}_{timestamp}{file_ext}"
        output_path = self.output_dir / output_filename

        if is_video:
            return await asyncio.to_thread(
                self._draw_and_save_video_sync,
                source_path, detection_boxes, output_path, compliance_status, compliance_alerts
            )
        return await asyncio.to_thread(
            self._draw_and_save_image_sync,
            source_path, detection_boxes, output_path, compliance_status, compliance_alerts
        )

    def _draw_and_save_image_sync(
        self,
        image_path: str,
        detection_boxes: list,
        output_path: Path,
        compliance_status: Optional[str] = None,
        compliance_alerts: Optional[list] = None
    ) -> str:
        """Desenha detecções em uma imagem e salva (síncrono, para uso com to_thread)."""
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

            # Se houver não conformidade, desenhar um banner de alerta vermelho no topo
            if compliance_status == "NAO_CONFORME":
                h, w = img.shape[:2]
                banner_h = max(50, int(h * 0.08))
                overlay = img.copy()
                cv2.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 255), -1)
                img = cv2.addWeighted(overlay, 0.7, img, 0.3, 0)

                alert_text = "ALERTA: NAO CONFORMIDADE!"
                alerts_str = " ".join(compliance_alerts or [])
                if "extintor" in alerts_str.lower() or "extinguidor" in alerts_str.lower():
                    alert_text = "ALERTA: EXTINTOR AUSENTE!"
                elif "epi" in alerts_str.lower() or "luvas" in alerts_str.lower() or "óculos" in alerts_str.lower():
                    alert_text = "ALERTA: NAO CONFORMIDADE DE EPI!"

                font_scale = banner_h / 80.0
                thickness = max(2, int(font_scale * 2))
                cv2.putText(
                    img,
                    alert_text,
                    (20, int(banner_h * 0.65)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    (255, 255, 255),
                    thickness,
                    cv2.LINE_AA
                )

            # Salvar imagem
            cv2.imwrite(str(output_path), img)
            logger.info("✅ Imagem analisada salva: %s", output_path)
            return str(output_path)
        except Exception as e:
            logger.error("❌ Erro ao salvar imagem analisada: %s", e)
            raise

    def _draw_and_save_video_sync(
        self,
        video_path: str,
        detection_boxes: list,
        output_path: Path,
        compliance_status: Optional[str] = None,
        compliance_alerts: Optional[list] = None
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
            # No Windows, usamos 'mp4v' por padrão para evitar que o OpenCV tente carregar
            # a DLL do OpenH264 e gere logs vermelhos de erro no console.
            import platform
            primary_codec = 'mp4v' if platform.system().lower() == "windows" else 'avc1'
            fourcc = cv2.VideoWriter_fourcc(*primary_codec)
            output_video = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

            if not output_video.isOpened() and primary_codec == 'avc1':
                logger.warning("⚠️ Não foi possível abrir o VideoWriter com 'avc1'. Tentando fallback para 'mp4v'...")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                output_video = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

            if not output_video.isOpened():
                cap.release()
                raise IOError(f"Não foi possível criar arquivo de vídeo (mp4v/avc1): {output_path}")

            # Agrupar boxes por frame
            boxes_by_frame = defaultdict(list)
            for box in detection_boxes:
                boxes_by_frame[box["frame_index"]].append(box)

            frame_idx = 0

            # Preparar textos do banner uma vez
            alert_text = "ALERTA: NAO CONFORMIDADE!"
            alerts_str = " ".join(compliance_alerts or [])
            if "extintor" in alerts_str.lower() or "extinguidor" in alerts_str.lower():
                alert_text = "ALERTA: EXTINTOR AUSENTE!"
            elif "epi" in alerts_str.lower() or "luvas" in alerts_str.lower() or "óculos" in alerts_str.lower():
                alert_text = "ALERTA: NAO CONFORMIDADE DE EPI!"

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

                # Se houver não conformidade, desenhar o banner vermelho em cada frame
                if compliance_status == "NAO_CONFORME":
                    h, w = frame.shape[:2]
                    banner_h = max(50, int(h * 0.08))
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 255), -1)
                    frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

                    font_scale = banner_h / 80.0
                    thickness = max(2, int(font_scale * 2))
                    cv2.putText(
                        frame,
                        alert_text,
                        (20, int(banner_h * 0.65)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale,
                        (255, 255, 255),
                        thickness,
                        cv2.LINE_AA
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

    def get_job_id_by_request_id(self, request_id: str) -> Optional[str]:
        """Retorna o job_id associado ao request_id, se existir."""
        return self.request_id_to_job_id.get(request_id)

    def register_request_id(self, request_id: str, job_id: str) -> None:
        """Associa um request_id a um job_id."""
        self.request_id_to_job_id[request_id] = job_id

    def create_job(self, job_id: str) -> None:
        """Registra um novo Job com contrapressão (fila cheia) e limpeza LRU de memória."""
        # 1. Controles de Contrapressão: verificar jobs ativos (PENDENTE ou PROCESSANDO)
        active_jobs = sum(1 for j in self.jobs.values() if j["status"] in ("PENDENTE", "PROCESSANDO"))
        if active_jobs >= settings.MAX_PENDING_JOBS:
            raise ValueError("Fila de processamento cheia. Por favor, tente novamente mais tarde.")

        # 2. Limpeza LRU: remover jobs concluídos/falhados mais antigos caso atinja o limite
        finished_jobs = [jid for jid, j in self.jobs.items() if j["status"] in ("CONCLUIDO", "FALHADO")]
        if len(self.jobs) >= settings.JOB_RETENTION_LIMIT and finished_jobs:
            # Como dicionários preservam ordem em Python 3.7+, deletamos o mais antigo
            oldest_job_id = finished_jobs[0]
            del self.jobs[oldest_job_id]
            
            # Remove o request_id correspondente no cache de idempotência
            req_ids_to_del = [req_id for req_id, jid in self.request_id_to_job_id.items() if jid == oldest_job_id]
            for req_id in req_ids_to_del:
                try:
                    del self.request_id_to_job_id[req_id]
                except KeyError:
                    pass

        self.jobs[job_id] = {
            "status": "PENDENTE",
            "result": None,
            "error": None
        }

    def update_job_status(self, job_id: str, status: str, result: Any = None, error: str = None) -> None:
        """Atualiza o status e/ou os resultados de um Job."""
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = status
            if result is not None:
                self.jobs[job_id]["result"] = result
            if error is not None:
                self.jobs[job_id]["error"] = error

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Busca os detalhes de um Job pelo ID."""
        return self.jobs.get(job_id)