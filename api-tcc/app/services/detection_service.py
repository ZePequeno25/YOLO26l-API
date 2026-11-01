"""
Detection service module.
Manages loading YOLO models, caching them, running inference on images and videos,
deduplicating bounding boxes, drawing detection results, and saving training artifacts.
"""
# pylint: disable=too-many-instance-attributes, too-many-locals, too-many-branches, too-many-statements
import asyncio
import json
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
import numpy as np
from fastapi import UploadFile
from ultralytics import YOLO

from app.services.compliance_service import compliance_service
from app.utils.test_simulator import simulate_video_from_image
from app.utils.translations import translate_class_name
from config.settings import settings

logger = logging.getLogger(__name__)

# Mapeamento de nomes amigáveis em português para as pastas físicas limpas no disco
MODEL_ALIASES = {
    "alimentos e utensílios": "alimentos_e_utensilios",
    "queda e epi": "queda_e_epis",
    "caixas e pessoas": "conteiner_e_canteiro",
    "caixas e pacotes": "caixas_e_pacotes",
    "extintor co2 e sílica": "extintor_co2_silica",
    "cones de segurança": "cone_seguranca",
    "óculos de proteção": "oculos_protecao",
    "vagas de estacionamento": "vagas_estacionamento",
    "escavadeira e carros": "escavadeira",
    "escavadeira": "escavadeira",
    "frascos e garrafas": "frascos_e_garrafas",
    "etiquetas e caixas": "etiquetas_e_caixas",
    "máquinas e obras": "caminhao_betoneira",
    "ônibus e caminhões": "veiculos_pesados",
    "coletes de segurança": "colete_seguranca",
    "máquinas pesadas": "maquinas_pesadas",
    "carros variados": "carro",
    "carro": "carro",
    "sinal de parque": "sinal_estacionamento",
    "sínal de parque": "sinal_estacionamento",
    "item caixa": "item_caixa",
    "extintor e sua sinalização": "extintor_co2_silica",
    "extintor de incêndio": "extintor_co2_silica",
    "cadeira": "cadeira",
    "caminhão": "caminhao",
    "caminho": "caminhao",
    "pessoa": "pessoa",
    "placa de sinalização": "placa_sinalizacao",
    "chuveiro de emergência": "chuveiro_emergencia",
    "submodelo_extintor_componentes": "submodelo_extintor_componentes",
    "submodelo_extintor_avarias": "submodelo_extintor_avarias",
    "submodelo_extintor_detalhes": "submodelo_extintor_detalhes",
    "submodelo_pressao_normal": "submodelo_pressao_normal"
}

REVERSE_MODEL_ALIASES = {v: k for k, v in MODEL_ALIASES.items()}

# Modelos desativados (Apenas Cadeira, Extintor de Incêndio e suas sobcamadas/submodelos permanecem ativos)
DISABLED_MODELS = {
    "alimentos e utensílios",
    "alimentos_e_utensilios",
    "frascos e garrafas",
    "frascos_e_garrafas",
    "queda e epi",
    "queda_e_epis",
    "caixas e pessoas",
    "conteiner_e_canteiro",
    "caixas e pacotes",
    "caixas_e_pacotes",
    "cones de segurança",
    "cone_seguranca",
    "óculos de proteção",
    "oculos_protecao",
    "vagas de estacionamento",
    "vagas_estacionamento",
    "escavadeira e carros",
    "escavadeira",
    "etiquetas e caixas",
    "etiquetas_e_caixas",
    "máquinas e obras",
    "caminhao_betoneira",
    "ônibus e caminhões",
    "veiculos_pesados",
    "coletes de segurança",
    "colete_seguranca",
    "máquinas pesadas",
    "maquinas_pesadas",
    "carros variados",
    "carro",
    "sinal de parque",
    "sínal de parque",
    "sinal_estacionamento",
    "item caixa",
    "item_caixa",
    "caminhão",
    "caminho",
    "caminhao",
    "pessoa",
    "chuveiro de emergência",
    "chuveiro_emergencia",
}


# Submodelos especialistas de sobcamada (ocultados da lista pública de modelos disponíveis pois são acionados automaticamente a partir da classe pai)
SUB_MODELS = {
    "placa_sinalizacao",
    "submodelo_extintor_componentes",
    "submodelo_extintor_avarias",
    "submodelo_extintor_detalhes",
    "submodelo_pressao_normal",
}




# Limiares de confiança sugeridos por classe/modelo (Média - 1.5*StdDev + 40% da Média)
CLASS_CONFIDENCE_THRESHOLDS = {
    # --- MODELOS E CLASSES ATIVAS ---
    "Adesivo / Rótulo": 0.30,
    "Arroz": 0.40,
    "Cadeira": 0.40,
    "Caixa": 0.56,
    "Caixa Aberta": 0.40,
    "Caixa Fechada": 0.40,
    "Caixa de Fundo": 0.40,
    "Caixas": 0.40,
    "Caminhão": 0.72,
    "Caminhão Betoneira": 0.42,
    "Caminhão Caçamba": 0.52,
    "Caminhão Extra Grande": 0.42,
    "Caminhão Grande": 0.40,
    "Caminhão Médio": 0.42,
    "Caminhão Pequeno": 0.40,
    "Capacete de Segurança": 0.45,
    "Carregadeira": 0.41,
    "Carro": 0.40,
    "Caçamba": 0.40,
    "Colete de Segurança": 0.60,
    "Cone de Segurança": 0.43,
    "Contêiner": 0.47,
    "Empilhadeira": 0.46,
    "Escada": 0.40,
    "Escavadeira": 0.40,
    "Etc Normal": 0.68,
    "Etiquetas": 0.40,
    "Extintor CO2 Babcock Davis": 0.40,
    "Extintor CO2 Walker MC-2A": 0.40,
    "Extintor CO2 e Sílica": 0.40,
    "Extintor Espuma Walker MF-60": 0.40,
    "Extintor Yamato YA-10NX": 0.40,
    "Extintor de Incêndio": 0.40,
    "Garrafa de Vidro Transparente": 0.54,
    "Gauge": 0.30,
    "Gauge Good": 0.30,
    "Gauge Low": 0.40,
    "Gauge Over": 0.95,
    "Gauge_Good": 0.30,
    "Guindaste Móvel": 0.40,
    "Handle": 0.30,
    "Hose": 0.30,
    "Hose Pipe": 0.30,
    "Lata": 0.61,
    "Lata de Doce": 0.51,
    "Mangueira / Difusor": 0.30,
    "Manômetro de Pressão": 0.30,
    "Melão": 0.48,
    "Miojo de Pacote": 0.51,
    "Motoniveladora": 0.40,
    "Máscara": 0.49,
    "Neve": 0.46,
    "Nozzle": 0.30,
    "Pacotes": 0.40,
    "Pessoa": 0.40,
    "Placa de Sinalização": 0.45,
    "Placa de Veículo": 0.48,
    "Produto": 0.59,
    "Queda Detectada": 0.41,
    "Rolinho Primavera": 0.51,
    "Rolo Compressor": 0.50,
    "Safety Pin": 0.30,
    "Safety_Pin": 0.30,
    "Sem Capacete de Segurança": 0.44,
    "Sem Colete de Segurança": 0.45,
    "Sem Máscara": 0.48,
    "Sem Óculos de Proteção": 0.45,
    "Shoutao": 0.52,
    "Sticker": 0.30,
    "Trator de Esteira (Bulldozer)": 0.45,
    "Trava / Lacre de Segurança": 0.30,
    "Vaga Ocupada": 0.40,
    "Vaga Vazia": 0.40,
    "cadeira": 0.40,
    "extintor co2 e sílica": 0.40,
    "extintor de incêndio": 0.40,
    "extintor e sua sinalização": 0.40,
    "placa de sinalização": 0.45,
    "placa_sinalizacao": 0.45,
    "submodelo_extintor_avarias": 0.40,
    "submodelo_extintor_componentes": 0.35,
    "submodelo_extintor_detalhes": 0.30,
    "submodelo_pressao_normal": 0.40,
    "Óculos de Proteção": 0.68,
    "Ônibus Grande": 0.66,
    "Ônibus Longo": 0.40,
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

        if model_name in DISABLED_MODELS or MODEL_ALIASES.get(model_name, model_name) in DISABLED_MODELS:
            logger.warning("Modelo solicitado '%s' está desativado. Usando modelo padrão '%s'.", model_name, self.default_model)
            model_name = getattr(self, 'default_model', "cadeira")

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
                # Pré-aquece o predictor para garantir 100% de determinismo desde a 1ª inferência
                dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
                list(model(dummy_img, verbose=False, conf=0.15, iou=settings.DETECTION_IOU_THRESHOLD, imgsz=640))
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
        iou_override: Optional[float] = None,
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
            # Força o overrides do Ultralytics mantendo formato consistente [img_size, img_size]
            target_sz = [img_size, img_size] if isinstance(img_size, int) else img_size
            model.overrides["imgsz"] = target_sz
            if hasattr(model, "predictor") and model.predictor is not None:
                model.predictor.args.imgsz = target_sz

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
                    infer_kwargs = {
                        "verbose": False,
                        "conf": conf_val,
                        "iou": iou_override if iou_override is not None else settings.DETECTION_IOU_THRESHOLD,
                        "imgsz": img_size,
                    }
                    if not is_openvino:
                        infer_kwargs["device"] = device
                    results = list(model(source, **infer_kwargs))
                    return results
                except Exception as ex_img:  # pylint: disable=broad-exception-caught
                    logger.warning("  ⚠️ model() falhou para imagem (%s): %s", model_name, ex_img)
                    return []

    def list_available_models(self) -> List[str]:
        """Lista apenas os modelos classe principais disponíveis (ocultando submodelos especialistas acionados por sobcamada/hierarquia)."""
        if not self.models_dir.exists():
            return []

        models = set()
        for folder in self.models_dir.iterdir():
            if folder.is_dir() and not folder.name.startswith('.'):
                pt_files = list(folder.glob("*.pt"))
                openvino_folders = list(folder.glob("*_openvino_model"))
                # Se tiver .pt OU se tiver pasta OpenVINO, considera disponível
                if pt_files or openvino_folders:
                    # Se for pasta de submodelo especialista, oculta da listagem pública de modelos primários
                    if folder.name.startswith("submodelo") or folder.name in SUB_MODELS:
                        # Expõe a classe pai 'extintor de incêndio' como modelo principal da hierarquia
                        if folder.name == "submodelo_extintor_componentes":
                            models.add("extintor de incêndio")
                        continue

                    alias_name = REVERSE_MODEL_ALIASES.get(folder.name, folder.name)
                    if alias_name in DISABLED_MODELS or folder.name in DISABLED_MODELS:
                        continue
                    if alias_name.startswith("submodelo") or alias_name in SUB_MODELS:
                        continue
                    models.add(alias_name)
        return sorted(list(models))


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
                "image/avif": ".avif",
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
            image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"]
            is_video = suffix in video_extensions or file_type in ["MP4/MOV", "AVI/WAV", "MKV"]
            is_image = (
                suffix in image_extensions
                or file_type in ["JPEG", "PNG", "GIF87", "GIF89", "WEBP", "AVIF"]
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
            class_frames = defaultdict(set)
            global_frames_with_detections = 0
            total_frames_processed = 0

            # Executar apenas o modelo solicitado para evitar desperdício de GPU e gargalos de concorrência.
            # Caso "all" seja enviado, executa a varredura APENAS dos modelos ativos e disponíveis.
            loop = asyncio.get_running_loop()
            models_to_run = []
            req_lower = requested_model.lower()
            is_extinguisher_request = req_lower in [
                "all", "todos", "extintor de incêndio", "extintor e sua sinalização",
                "extintor co2 e sílica", "extintor_co2_silica", "submodelo_extintor_componentes",
                "placa de sinalização", "placa_sinalizacao"
            ]

            if req_lower in ["all", "todos"]:
                models_to_run = self.available_models
            else:
                resolved_alias = REVERSE_MODEL_ALIASES.get(requested_model, requested_model)
                if is_extinguisher_request or resolved_alias in ["extintor_co2_silica", "submodelo_extintor_componentes", "extintor de incêndio"]:
                    models_to_run = ["extintor_co2_silica", "submodelo_extintor_componentes"]
                    is_extinguisher_request = True
                elif resolved_alias in self.available_models:
                    models_to_run = [resolved_alias]
                else:
                    default_alias = REVERSE_MODEL_ALIASES.get(self.default_model, self.default_model)
                    models_to_run = [default_alias]

            # Garantia estrita de que nenhum modelo desativado seja executado mesmo se solicitado
            models_to_run = [
                m for m in models_to_run
                if m not in DISABLED_MODELS and MODEL_ALIASES.get(m, m) not in DISABLED_MODELS
            ]
            if not models_to_run:
                models_to_run = self.available_models

            logger.info("⚡ Executando inferência para os modelos ativos: %s", models_to_run)

            if not is_video and is_extinguisher_request:
                img_cv_scene = cv2.imread(tmp_path)
                if img_cv_scene is not None:
                    total_frames_processed = 1
                    ext_scene_boxes = self._analyze_extinguisher_scene(img_cv_scene, 0)
                    all_detection_boxes.extend(ext_scene_boxes)
                    if ext_scene_boxes:
                        global_frames_with_detections = 1
                        for b in ext_scene_boxes:
                            global_class_counts[b["class_name"]] += 1

                # Se "all" foi solicitado e nada de extintor/placa foi encontrado, rodar os demais modelos (ex: cadeira)
                other_models = [
                    m for m in models_to_run
                    if m not in ["extintor_co2_silica", "submodelo_extintor_componentes", "extintor de incêndio", "extintor e sua sinalização", "extintor co2 e sílica"]
                ]
                if other_models and not all_detection_boxes:
                    tasks = [
                        loop.run_in_executor(
                            self.executor,
                            self._run_single_model_inference,
                            current_model_name,
                            tmp_path,
                            is_video
                        )
                        for current_model_name in other_models
                    ]
                    models_results = await asyncio.gather(*tasks)
                    for current_model_name, results in zip(other_models, models_results):
                        for frame_idx, result in enumerate(results):
                            if not result.boxes or len(result.boxes) == 0:
                                continue
                            global_frames_with_detections = 1
                            names = result.names
                            for box in result.boxes:
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                class_id = int(box.cls.item())
                                confidence = float(box.conf.item())
                                class_name = translate_class_name(names[int(class_id)])
                                target_threshold = CLASS_CONFIDENCE_THRESHOLDS.get(
                                    class_name, settings.DETECTION_CONF_THRESHOLD
                                )
                                if confidence < target_threshold:
                                    continue
                                all_detection_boxes.append({
                                    "frame_index": frame_idx,
                                    "class_id": class_id,
                                    "class_name": class_name,
                                    "confidence": confidence,
                                    "x1": x1,
                                    "y1": y1,
                                    "x2": x2,
                                    "y2": y2,
                                    "track_id": None,
                                    "model_source": current_model_name
                                })
                                global_class_counts[class_name] += 1
            else:
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

                            class_frames[class_name].add(frame_idx)

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

            # --- FILTRO TEMPORAL E VALIDAÇÃO ESTRITA DE VÍDEOS ---
            if is_video and total_frames_processed > 5:
                min_video_frames = max(3, int(total_frames_processed * 0.08))
                
                # Checar se existem componentes essenciais de extintor na cena toda
                has_global_extinguisher_core = any(
                    any(core in b.get("class_name", "").lower() for core in ["handle", "gauge_good", "gauge", "safety", "nozzle"])
                    for b in all_detection_boxes
                )

                filtered_classes = set()
                for name in list(global_class_counts.keys()):
                    name_lower = name.lower()
                    appear_count = len(class_frames[name])
                    max_conf = max([b["confidence"] for b in all_detection_boxes if b["class_name"] == name], default=0.0)

                    # Se for classe de extintor principal
                    if any(k in name_lower for k in ["extintor", "babcock", "walker", "yamato"]):
                        # Descarta se tiver pouca persistência temporal OU se não tiver componente estrutural na cena
                        if appear_count < min_video_frames or not has_global_extinguisher_core:
                            logger.info(
                                "⚠️ [Filtro Vídeo] Removendo falso positivo de extintor '%s' (quadros: %d/%d, core_component: %s, max_conf: %.2f)",
                                name, appear_count, total_frames_processed, has_global_extinguisher_core, max_conf
                            )
                            filtered_classes.add(name)
                    elif appear_count < min_video_frames and max_conf < 0.95:
                        logger.info("⚠️ [Filtro Vídeo] Removendo ruído transiente '%s' (%d/%d quadros)", name, appear_count, total_frames_processed)
                        filtered_classes.add(name)

                for fclass in filtered_classes:
                    global_class_counts.pop(fclass, None)
                    global_unique_objects.pop(fclass, None)

                all_detection_boxes = [b for b in all_detection_boxes if b["class_name"] not in filtered_classes]

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
            if compliance_result["status"] == "NAO_CONFORME":
                compliance_result["status"] = "NÃO CONFORME"

            # Executar análise em sobcamada (Sub-layer Inspection)
            from app.services.sublayer_service import sub_layer_manager
            sub_layer_results = []
            img_cv_sub = cv2.imread(tmp_path) if (not is_video and os.path.exists(tmp_path)) else None

            valid_detection_boxes = []
            for box in all_detection_boxes:
                cname = box.get("class_name")
                msource = (box.get("model_source") or "").lower()
                # Caixas de componentes do submodelo ou placas de sinalização não devem disparar auto-inspeção recursiva como objeto pai
                if "submodelo" in msource or cname in (
                    "Placa de Sinalização", "Handle", "Manômetro de Pressão",
                    "Mangueira / Difusor", "Trava / Lacre de Segurança", "Adesivo / Rótulo"
                ):
                    valid_detection_boxes.append(box)
                    continue

                roi = None
                if img_cv_sub is not None:
                    x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
                    pad_w = int((x2 - x1) * 0.10)
                    pad_h = int((y2 - y1) * 0.10)
                    roi = img_cv_sub[max(0, y1 - pad_h):min(img_h, y2 + pad_h), max(0, x1 - pad_w):min(img_w, x2 + pad_w)]
                res = sub_layer_manager.inspect_cropped_roi(cname, roi, context_boxes=all_detection_boxes)
                if res.get("has_sub_layer"):
                    specialist_dets = res.get("specialist_detections", [])
                    cname_lower = cname.lower()
                    # Validação estrita de sobcamada para extintor: exige pelo menos 1 componente estrutural essencial
                    if any(k in cname_lower for k in ["extintor", "babcock", "walker", "yamato", "fire"]):
                        has_core_component = any(
                            any(
                                core in f"{d.get('class_name', '')} {d.get('translated_name', '')}".lower()
                                for core in ["handle", "gauge_good", "gauge", "hose", "nozzle", "safety pin", "safety_pin", "manômetro", "mangueira", "trava"]
                            )
                            for d in specialist_dets
                        )
                        if not has_core_component and box.get("confidence", 0) < 0.95:
                            logger.info("⚠️ Falso positivo descartado para '%s' (conf: %.2f) sem componente estrutural chave na sobcamada.", cname, box.get("confidence", 0))
                            continue
                    elif len(specialist_dets) == 0 and box.get("confidence", 0) < 0.95:
                        logger.info("⚠️ Falso positivo descartado para '%s' (conf: %.2f) sem componentes no submodelo.", cname, box.get("confidence", 0))
                        continue
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
                valid_detection_boxes.append(box)

            all_detection_boxes = valid_detection_boxes
            # Atualizar final_counts com apenas as caixas validadas
            final_counts = defaultdict(int)
            for b in all_detection_boxes:
                final_counts[b["class_name"]] += 1

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

            # Gerar laudo IA (Ollama) APENAS quando objetos forem encontrados
            compliance_report = None
            if settings.ENABLE_PERSONALIZED_MESSAGE and final_counts:
                try:
                    from app.services.ollama_message_service import ollama_message_service
                    analysis_dict = {
                        "class_counts": final_counts,
                        "compliance_status": compliance_result["status"],
                        "compliance_alerts": compliance_result["alerts"],
                        "sub_layer_analysis": sub_layer_results
                    }
                    compliance_report = ollama_message_service.generate_personalized_message(
                        analysis_dict, requested_model
                    )
                except Exception as report_err:
                    logger.error("⚠️ Erro ao gerar laudo Ollama: %s", report_err)
                    compliance_report = None

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
                "compliance_report": compliance_report,
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

    def analyze_image_bytes(
        self,
        content: bytes,
        filename: str,
        model_name: Optional[str] = None,
        log_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        Analisa uma imagem de forma síncrona e determinística (mesmo pipeline de _analyze_internal),
        retornando contagens, caixas, sobcamada, status de conformidade, alertas e laudo Ollama.
        """
        requested_model = self._validate_model_name(
            model_name or getattr(self, "default_model", "cadeira")
        )
        suffix = os.path.splitext(filename)[1].lower() or ".jpg"
        tmp_path = f"temp_{uuid4().hex}{suffix}"
        try:
            with open(tmp_path, "wb") as f:
                f.write(content)
            img_cv = cv2.imread(tmp_path)
            if img_cv is None:
                raise ValueError(f"Não foi possível decodificar a imagem: {filename}")
            img_h, img_w = img_cv.shape[:2]

            all_detection_boxes = self._analyze_extinguisher_scene(img_cv, 0)

            compliance_result = compliance_service.evaluate(
                all_detection_boxes, image_width=img_w, image_height=img_h
            )
            if compliance_result["status"] == "NAO_CONFORME":
                compliance_result["status"] = "NÃO CONFORME"

            from app.services.sublayer_service import sub_layer_manager
            sub_layer_results = []
            valid_detection_boxes = []

            for box in all_detection_boxes:
                cname = box.get("class_name")
                msource = (box.get("model_source") or "").lower()
                if "submodelo" in msource or cname in (
                    "Placa de Sinalização", "Handle", "Manômetro de Pressão",
                    "Mangueira / Difusor", "Trava / Lacre de Segurança", "Adesivo / Rótulo"
                ):
                    valid_detection_boxes.append(box)
                    continue

                x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
                pad_w = int((x2 - x1) * 0.10)
                pad_h = int((y2 - y1) * 0.10)
                roi = img_cv[max(0, y1 - pad_h):min(img_h, y2 + pad_h), max(0, x1 - pad_w):min(img_w, x2 + pad_w)]
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
                valid_detection_boxes.append(box)

            all_detection_boxes = valid_detection_boxes
            final_counts = defaultdict(int)
            for b in all_detection_boxes:
                final_counts[b["class_name"]] += 1

            if log_to_db:
                try:
                    from app.core.database_metrics import log_prediction
                    log_prediction(
                        filename,
                        requested_model,
                        dict(final_counts),
                        1,
                        compliance_result["status"],
                        all_detection_boxes,
                    )
                except Exception as log_err:
                    logger.debug("Aviso ao registrar métricas: %s", log_err)

            compliance_report = None
            if final_counts:
                try:
                    from app.services.ollama_message_service import ollama_message_service
                    analysis_dict = {
                        "class_counts": dict(final_counts),
                        "compliance_status": compliance_result["status"],
                        "compliance_alerts": compliance_result["alerts"],
                        "sub_layer_analysis": sub_layer_results,
                    }
                    compliance_report = ollama_message_service.generate_personalized_message(
                        analysis_dict, requested_model
                    )
                except Exception:
                    compliance_report = None

            return {
                "requested_model": requested_model,
                "class_counts": dict(final_counts),
                "num_frames_processed": 1,
                "frames_with_detections": 1 if final_counts else 0,
                "analyzed_file": None,
                "analyzed_output": None,
                "boxes": all_detection_boxes,
                "compliance_status": compliance_result["status"],
                "compliance_alerts": compliance_result["alerts"],
                "compliance_report": compliance_report,
                "sub_layer_analysis": sub_layer_results,
            }
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def _analyze_extinguisher_scene(self, img_cv: np.ndarray, frame_index: int = 0) -> List[Dict[str, Any]]:
        """
        Executa inferência integrada e determinística dos modelos de Extintor, Placa de Sinalização
        e Submodelos especialistas (detalhes, componentes, avarias), distinguindo:
        1. Cenas de Placa sem Extintor (2D) -> Retorna apenas 'Placa de Sinalização'.
        2. Cenas de Extintor com Placa (3D + Sinalização) -> Retorna Extintor + Placa de Sinalização + Submodelos.
        3. Cenas de Extintor sem Placa (3D sem Sinalização) -> Retorna Extintor + Submodelos.
        """
        if img_cv is None or img_cv.size == 0:
            return []

        h, w = img_cv.shape[:2]
        specialist_models = [
            "extintor_co2_silica",
            "placa_sinalizacao",
            "submodelo_extintor_componentes",
            "submodelo_extintor_avarias",
            "submodelo_extintor_detalhes",
        ]
        if not getattr(self, "_specialist_models_warmed_up", False):
            for m_name in specialist_models:
                try:
                    self.get_model(m_name)
                except Exception:
                    pass
            for m_name in specialist_models:
                try:
                    self._run_single_model_inference(
                        model_name=m_name,
                        source=img_cv,
                        is_video=False,
                        conf_override=0.15,
                        imgsz_override=640,
                        iou_override=0.70,
                    )
                except Exception:
                    pass
            self._specialist_models_warmed_up = True

        dets_by_model: Dict[str, List[Dict[str, Any]]] = {}
        for m_name in specialist_models:
            try:
                res_list = self._run_single_model_inference(
                    model_name=m_name,
                    source=img_cv,
                    is_video=False,
                    conf_override=0.15,
                    imgsz_override=640,
                    iou_override=0.70,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("Falha ao executar modelo especialista '%s': %s", m_name, exc)
                res_list = []

            items = []
            if res_list:
                for r in res_list:
                    if hasattr(r, "boxes") and r.boxes is not None:
                        names = getattr(r, "names", {}) or {}
                        for b in r.boxes:
                            cid = int(b.cls[0].item())
                            conf = float(b.conf[0].item())
                            raw_cname = names.get(cid, str(cid))
                            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                            items.append({
                                "cls_id": cid,
                                "raw_class": raw_cname,
                                "conf": conf,
                                "box": (x1, y1, x2, y2),
                            })
            dets_by_model[m_name] = items

        det_thresh = CLASS_CONFIDENCE_THRESHOLDS.get("submodelo_extintor_detalhes", 0.30)
        det_mech = [
            d for d in dets_by_model.get("submodelo_extintor_detalhes", [])
            if d["raw_class"] in ("handle", "hose_pipe", "gauge", "safety_pin", "nozzle")
            and d["conf"] >= det_thresh
        ]

        # Caso 1: Cena contendo apenas Placa de Sinalização 2D (sem componentes mecânicos 3D de extintor)
        if not det_mech:
            sign_candidates = []
            placa_thresh = CLASS_CONFIDENCE_THRESHOLDS.get("Placa de Sinalização", 0.45)
            for d in dets_by_model.get("submodelo_extintor_detalhes", []):
                if d["raw_class"] == "sticker" and d["conf"] >= max(0.50, placa_thresh):
                    x1, y1, x2, y2 = d["box"]
                    sign_candidates.append({
                        "frame_index": frame_index,
                        "class_id": 0,
                        "class_name": "Placa de Sinalização",
                        "raw_class_name": "fire_extinguisher_sign",
                        "confidence": round(d["conf"], 4),
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "track_id": None,
                        "model_source": "placa_sinalizacao",
                    })
            for d in dets_by_model.get("placa_sinalizacao", []):
                if d["conf"] >= placa_thresh:
                    x1, y1, x2, y2 = d["box"]
                    sign_candidates.append({
                        "frame_index": frame_index,
                        "class_id": 0,
                        "class_name": "Placa de Sinalização",
                        "raw_class_name": "fire_extinguisher_sign",
                        "confidence": round(d["conf"], 4),
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "track_id": None,
                        "model_source": "placa_sinalizacao",
                    })
            return self._deduplicate_boxes_by_iou(sign_candidates, 0.45)

        # Caso 2 e 3: Extintor 3D real presente na cena (validado por componentes mecânicos em submodelo_extintor_detalhes)
        scene_boxes: List[Dict[str, Any]] = []

        # A. Caixas do Extintor Principal
        ext_thresh = min(
            CLASS_CONFIDENCE_THRESHOLDS.get("Extintor de Incêndio", 0.40),
            0.35
        )
        primary_ext_candidates = []
        for d in dets_by_model.get("extintor_co2_silica", []):
            if d["conf"] >= ext_thresh:
                x1, y1, x2, y2 = d["box"]
                translated = translate_class_name(d["raw_class"])
                primary_ext_candidates.append({
                    "frame_index": frame_index,
                    "class_id": d["cls_id"],
                    "class_name": translated,
                    "raw_class_name": d["raw_class"],
                    "confidence": round(d["conf"], 4),
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "track_id": None,
                    "model_source": "extintor_co2_silica",
                })

        if not primary_ext_candidates:
            avarias_thresh = CLASS_CONFIDENCE_THRESHOLDS.get("submodelo_extintor_avarias", 0.40)
            for d in dets_by_model.get("submodelo_extintor_avarias", []):
                if "extinguisher" in d["raw_class"].lower() and d["conf"] >= avarias_thresh:
                    x1, y1, x2, y2 = d["box"]
                    primary_ext_candidates.append({
                        "frame_index": frame_index,
                        "class_id": d["cls_id"],
                        "class_name": "Extintor de Incêndio",
                        "raw_class_name": d["raw_class"],
                        "confidence": round(d["conf"], 4),
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "track_id": None,
                        "model_source": "extintor_co2_silica",
                    })

        if not primary_ext_candidates:
            mx1 = min(d["box"][0] for d in det_mech)
            my1 = min(d["box"][1] for d in det_mech)
            mx2 = max(d["box"][2] for d in det_mech)
            my2 = max(d["box"][3] for d in det_mech)
            best_conf = max(d["conf"] for d in det_mech)
            primary_ext_candidates.append({
                "frame_index": frame_index,
                "class_id": 0,
                "class_name": "Extintor de Incêndio",
                "raw_class_name": "fire extinguisher",
                "confidence": round(best_conf, 4),
                "x1": mx1,
                "y1": my1,
                "x2": mx2,
                "y2": min(h, my2 + int((my2 - my1) * 1.5)),
                "track_id": None,
                "model_source": "extintor_co2_silica",
            })

        deduped_exts = self._deduplicate_boxes_by_iou(primary_ext_candidates, 0.45)
        scene_boxes.extend(deduped_exts)

        # B. Detecção de Placa de Sinalização de Parede / Kit
        valve_boxes = [
            d["box"] for d in dets_by_model.get("submodelo_extintor_detalhes", [])
            if d["raw_class"] in ("handle", "gauge") and d["conf"] >= 0.50
        ]
        if not valve_boxes:
            valve_boxes = [
                d["box"] for d in dets_by_model.get("submodelo_extintor_detalhes", [])
                if d["raw_class"] in ("handle", "gauge") and d["conf"] >= 0.30
            ]
        if valve_boxes:
            min_valve_y1 = min(b[1] for b in valve_boxes)
        else:
            comp_handles = [
                d["box"] for d in dets_by_model.get("submodelo_extintor_componentes", [])
                if d["raw_class"] == "handle" and d["conf"] >= 0.20
            ]
            min_valve_y1 = max((b[1] for b in comp_handles), default=int(0.25 * h))

        wall_sign_candidates = []
        # Regra 1: Placa detectada como sticker acima da válvula do extintor
        for src in ("submodelo_extintor_detalhes", "submodelo_extintor_componentes"):
            for d in dets_by_model.get(src, []):
                if d["raw_class"] == "sticker" and d["conf"] >= 0.20:
                    x1, y1, x2, y2 = d["box"]
                    bw, bh = x2 - x1, y2 - y1
                    if bw < 0.035 * w or bh < 0.06 * h:
                        continue
                    if bw < 0.05 * w and y1 < 0.05 * h:
                        continue
                    if bw > 0.70 * w and bh > 0.70 * h:
                        continue
                    cy = (y1 + y2) / 2.0
                    if y2 <= min_valve_y1 + int(0.02 * h) or (y1 < min_valve_y1 and cy < min_valve_y1 * 0.85):
                        wall_sign_candidates.append({
                            "frame_index": frame_index,
                            "class_id": 0,
                            "class_name": "Placa de Sinalização",
                            "raw_class_name": "fire_extinguisher_sign",
                            "confidence": round(max(0.50, d["conf"]), 4),
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "track_id": None,
                            "model_source": "placa_sinalizacao",
                        })

        # Regra 2: Placa quadrada de alta confiança (>= 0.85) fora do eixo horizontal do cilindro
        mech_xs = [
            (m["box"][0] + m["box"][2]) / 2.0
            for m in det_mech
            if m["raw_class"] in ("gauge", "hose_pipe")
        ]
        for d in dets_by_model.get("submodelo_extintor_detalhes", []):
            if d["raw_class"] == "sticker" and d["conf"] >= 0.85:
                x1, y1, x2, y2 = d["box"]
                bw, bh = x2 - x1, y2 - y1
                aspect = bw / float(max(1, bh))
                cx = (x1 + x2) / 2.0
                if mech_xs and all(abs(cx - mx) > 0.25 * w for mx in mech_xs) and 0.75 <= aspect <= 1.35:
                    wall_sign_candidates.append({
                        "frame_index": frame_index,
                        "class_id": 0,
                        "class_name": "Placa de Sinalização",
                        "raw_class_name": "fire_extinguisher_sign",
                        "confidence": round(d["conf"], 4),
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "track_id": None,
                        "model_source": "placa_sinalizacao",
                    })

        # Regra 3: Placa retangular vermelha/verde com pictograma branco estritamente acima da válvula
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0, 90, 90]), np.array([12, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([165, 90, 90]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(m1, m2)
        green_mask = cv2.inRange(hsv, np.array([45, 70, 100]), np.array([90, 255, 255]))
        white_mask = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 60, 255]))
        kernel = np.ones((3, 3), np.uint8)
        for mask in (red_mask, green_mask):
            closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in cnts:
                rx, ry, rw, rh = cv2.boundingRect(cnt)
                area = rw * rh
                if area < (w * h * 0.004) or area > (w * h * 0.35):
                    continue
                if rw < 0.05 * w or rh < 0.05 * h:
                    continue
                aspect = rw / float(rh)
                if not (0.50 <= aspect <= 2.5):
                    continue
                rect_fill = cv2.countNonZero(closed[ry:ry + rh, rx:rx + rw]) / float(area)
                white_fill = cv2.countNonZero(white_mask[ry:ry + rh, rx:rx + rw]) / float(area)
                if rect_fill >= 0.50 and 0.12 <= white_fill <= 0.55 and (ry + rh) <= min_valve_y1:
                    wall_sign_candidates.append({
                        "frame_index": frame_index,
                        "class_id": 0,
                        "class_name": "Placa de Sinalização",
                        "raw_class_name": "fire_extinguisher_sign",
                        "confidence": round(float(rect_fill), 4),
                        "x1": rx,
                        "y1": ry,
                        "x2": rx + rw,
                        "y2": ry + rh,
                        "track_id": None,
                        "model_source": "placa_sinalizacao",
                    })

        deduped_signs = self._deduplicate_boxes_by_iou(wall_sign_candidates, 0.40)
        scene_boxes.extend(deduped_signs)

        # C. Componentes de Submodelo do Extintor
        submodel_map = {
            "handle": "Handle",
            "gauge": "Manômetro de Pressão",
            "gauge_good": "Manômetro de Pressão",
            "hose_pipe": "Mangueira / Difusor",
            "hose pipe": "Mangueira / Difusor",
            "hose": "Mangueira / Difusor",
            "nozzle": "Mangueira / Difusor",
            "safety_pin": "Trava / Lacre de Segurança",
            "safety pin": "Trava / Lacre de Segurança",
            "sticker": "Adesivo / Rótulo",
        }
        sub_boxes_by_class: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        comp_thresh = CLASS_CONFIDENCE_THRESHOLDS.get("submodelo_extintor_componentes", 0.35)

        for src, min_c in (("submodelo_extintor_detalhes", det_thresh), ("submodelo_extintor_componentes", comp_thresh)):
            for d in dets_by_model.get(src, []):
                r_cls = d["raw_class"].lower()
                if d["conf"] < min_c or r_cls not in submodel_map:
                    continue
                x1, y1, x2, y2 = d["box"]
                cand_box = {
                    "frame_index": frame_index,
                    "class_id": d["cls_id"],
                    "class_name": submodel_map[r_cls],
                    "raw_class_name": d["raw_class"],
                    "confidence": round(d["conf"], 4),
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "track_id": None,
                    "model_source": src,
                }
                if r_cls == "sticker":
                    if y2 <= min_valve_y1 + int(0.02 * h):
                        continue
                    if any(self._calculate_iou(cand_box, sb) >= 0.25 for sb in deduped_signs):
                        continue
                sub_boxes_by_class[submodel_map[r_cls]].append(cand_box)

        for _, s_list in sub_boxes_by_class.items():
            scene_boxes.extend(self._deduplicate_boxes_by_iou(s_list, 0.45))

        return scene_boxes

    @staticmethod
    def _compute_box_iou(b1: Dict[str, Any], b2: Dict[str, Any]) -> float:
        """Calcula IoU (Intersection over Union) entre duas caixas delimitadoras."""
        inter_x1 = max(b1["x1_raw"], b2["x1_raw"])
        inter_y1 = max(b1["y1_raw"], b2["y1_raw"])
        inter_x2 = min(b1["x2_raw"], b2["x2_raw"])
        inter_y2 = min(b1["y2_raw"], b2["y2_raw"])

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area1 = max(0, b1["x2_raw"] - b1["x1_raw"]) * max(0, b1["y2_raw"] - b1["y1_raw"])
        area2 = max(0, b2["x2_raw"] - b2["x1_raw"]) * max(0, b2["y2_raw"] - b2["y1_raw"])

        union_area = float(area1 + area2 - inter_area)
        if union_area <= 0:
            return 0.0
        return inter_area / union_area

    @staticmethod
    def _extract_raw_boxes_from_results(results: List[Any], model_source: str) -> List[Dict[str, Any]]:
        """Extrai caixas brutas em espaço 640x640 de uma rodada de inferência."""
        raw_boxes = []
        for result in results:
            if not result.boxes or len(result.boxes) == 0:
                continue
            names = result.names
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                raw_class_name = names.get(cls_id, str(cls_id)) if names else str(cls_id)
                class_name = translate_class_name(raw_class_name)

                xyxy = box.xyxy[0].cpu().numpy()
                x1_raw = int(round(xyxy[0]))
                y1_raw = int(round(xyxy[1]))
                x2_raw = int(round(xyxy[2]))
                y2_raw = int(round(xyxy[3]))

                raw_boxes.append({
                    "cls_id": cls_id,
                    "class_name": class_name,
                    "raw_class_name": raw_class_name,
                    "confidence": confidence,
                    "x1_raw": x1_raw,
                    "y1_raw": y1_raw,
                    "x2_raw": x2_raw,
                    "y2_raw": y2_raw,
                    "model_source": model_source
                })
        return raw_boxes

    async def analyze_frame(
        self,
        frame: Any,
        frame_index: int = 0,
        model_name: Optional[str] = None,
        min_confidence: float = 0.25,
        disable_compliance: bool = False,
        imgsz: int = 640,
    ) -> Dict[str, Any]:
        """
        Executa inferência de modelos em um frame (numpy array) na memória com Verificação Múltipla (Dupla Passagem).
        Apenas objetos pai validados no consenso de dupla inferência e que atinjam o limiar passam para sobcamadas.
        """
        all_detection_boxes = []
        global_class_counts = defaultdict(int)

        loop = asyncio.get_running_loop()

        # 1. Trata seleção de modelos para tempo real
        if model_name:
            clean_name = model_name.strip().lower()
            if clean_name in ["all", "todos"]:
                models_to_run = self.available_models
            elif "," in model_name:
                requested_list = [m.strip() for m in model_name.split(",") if m.strip()]
                models_to_run = [m for m in requested_list if m in self.available_models]
                if not models_to_run:
                    logger.warning("Nenhum modelo da lista '%s' disponível/ativo. Usando modelos ativos.", model_name)
                    models_to_run = self.available_models
            elif model_name in self.available_models:
                models_to_run = [model_name]
            else:
                resolved_alias = REVERSE_MODEL_ALIASES.get(model_name, model_name)
                if resolved_alias in self.available_models:
                    models_to_run = [resolved_alias]
                else:
                    logger.warning("Modelo solicitado '%s' está desativado. Usando modelos ativos.", model_name)
                    models_to_run = self.available_models
        else:
            models_to_run = self.available_models

        # Garantia estrita de que nenhum modelo desativado seja executado no tempo real
        models_to_run = [
            m for m in models_to_run
            if m not in DISABLED_MODELS and MODEL_ALIASES.get(m, m) not in DISABLED_MODELS
        ]
        if not models_to_run:
            models_to_run = self.available_models

        # 2. Pré-redimensionamento RAM (Visão 1 e Visão 2 para Verificação Múltipla)
        target_imgsz = 640
        orig_h, orig_w = frame.shape[:2]
        if orig_h != target_imgsz or orig_w != target_imgsz:
            resized_frame_p1 = cv2.resize(frame, (target_imgsz, target_imgsz))
        else:
            resized_frame_p1 = frame

        # Passo 2 (visualização espelhada para validação cruzada do objeto pai)
        resized_frame_p2 = cv2.flip(resized_frame_p1, 1)

        scale_x = orig_w / float(target_imgsz)
        scale_y = orig_h / float(target_imgsz)

        # Disparar Passo 1 e Passo 2 simultaneamente em paralelo (Dupla Inferência 1.5x)
        tasks_p1 = [
            loop.run_in_executor(
                self.executor,
                self._run_single_model_inference,
                current_model_name,
                resized_frame_p1,
                False,
                0.20,  # Coleta inicial ampla para cruzamento
                target_imgsz
            )
            for current_model_name in models_to_run
        ]

        tasks_p2 = [
            loop.run_in_executor(
                self.executor,
                self._run_single_model_inference,
                current_model_name,
                resized_frame_p2,
                False,
                0.20,
                target_imgsz
            )
            for current_model_name in models_to_run
        ]

        all_results_p1, all_results_p2 = await asyncio.gather(
            asyncio.gather(*tasks_p1),
            asyncio.gather(*tasks_p2)
        )

        p1_raw_boxes = []
        for current_model_name, results in zip(models_to_run, all_results_p1):
            if results:
                p1_raw_boxes.extend(self._extract_raw_boxes_from_results(results, current_model_name))

        p2_raw_boxes = []
        for current_model_name, results in zip(models_to_run, all_results_p2):
            if results:
                p2_raw_boxes.extend(self._extract_raw_boxes_from_results(results, current_model_name))

        # 3. Consenso de Verificação Múltipla do Objeto Pai
        max_detections_per_frame = defaultdict(int)

        for b1 in p1_raw_boxes:
            cname = b1["class_name"]
            conf_1 = b1["confidence"]

            best_p2_conf = 0.0
            found_match = False

            for b2 in p2_raw_boxes:
                c1_lower = cname.lower()
                c2_lower = b2["class_name"].lower()

                # Mesma classe ou mesma família pai (ex: variantes de extintor de incêndio)
                is_same_family = (
                    c1_lower == c2_lower
                    or (
                        any(k in c1_lower for k in ["extintor", "babcock", "walker", "yamato"])
                        and any(k in c2_lower for k in ["extintor", "babcock", "walker", "yamato"])
                    )
                )
                if not is_same_family:
                    continue

                # Inverter coordenada X de b2 (já que P2 usou flip horizontal na imagem de 640x640)
                b2_unflip = {
                    "class_name": b2["class_name"],
                    "x1_raw": target_imgsz - b2["x2_raw"],
                    "y1_raw": b2["y1_raw"],
                    "x2_raw": target_imgsz - b2["x1_raw"],
                    "y2_raw": b2["y2_raw"]
                }

                iou = self._compute_box_iou(b1, b2_unflip)
                if iou >= 0.20:
                    found_match = True
                    best_p2_conf = max(best_p2_conf, b2["confidence"])

            # Média e validação cruzada entre as duas inferências
            if found_match:
                combined_conf = (conf_1 + best_p2_conf) / 2.0
            else:
                combined_conf = conf_1 / 2.0  # Penaliza caixas não confirmadas na verificação múltipla

            # Limiar do objeto pai para seguir para sobcamadas
            if any(k in cname.lower() for k in ["extintor", "babcock", "walker", "yamato"]):
                target_thresh = max(min_confidence, 0.40)
            else:
                target_thresh = max(
                    min_confidence,
                    CLASS_CONFIDENCE_THRESHOLDS.get(cname, settings.DETECTION_CONF_THRESHOLD)
                )

            # Requisito estrito: aceita APENAS se for confirmado pela verificação dupla E a média atingir o limiar
            if found_match and combined_conf >= target_thresh:
                x1 = int(round(b1["x1_raw"] * scale_x))
                y1 = int(round(b1["y1_raw"] * scale_y))
                x2 = int(round(b1["x2_raw"] * scale_x))
                y2 = int(round(b1["y2_raw"] * scale_y))
                w_box = max(0, x2 - x1)
                h_box = max(0, y2 - y1)

                all_detection_boxes.append({
                    "class_id": b1["cls_id"],
                    "class_name": cname,
                    "raw_class_name": b1["raw_class_name"],
                    "confidence": round(combined_conf, 4),
                    "certainty_percent": f"{round(combined_conf * 100, 2)}%",
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "width": w_box,
                    "height": h_box,
                    "area": w_box * h_box,
                    "track_id": None,
                    "model_source": b1["model_source"],
                    "multi_pass_confirmed": True
                })
                max_detections_per_frame[cname] += 1
            else:
                logger.info("❌ Objeto '%s' descartado na verificação múltipla (p1: %.2f, p2: %.2f, média: %.2f < %.2f)",
                            cname, conf_1, best_p2_conf, combined_conf, target_thresh)

        # 4. Inspeção em Sobcamada sobre o recorte (RoI) dos objetos pai validados
        sub_layer_results = []
        valid_boxes = []
        h, w = frame.shape[:2]

        if all_detection_boxes:
            from app.services.sublayer_service import sub_layer_manager
            for b_item in all_detection_boxes:
                cname = b_item.get("class_name")
                cname_lower = cname.lower()
                x1, y1, x2, y2 = b_item["x1"], b_item["y1"], b_item["x2"], b_item["y2"]
                pad_w = int((x2 - x1) * 0.10)
                pad_h = int((y2 - y1) * 0.10)
                roi = frame[max(0, y1 - pad_h):min(h, y2 + pad_h), max(0, x1 - pad_w):min(w, x2 + pad_w)]

                res = sub_layer_manager.inspect_cropped_roi(cname, roi, context_boxes=all_detection_boxes)
                if res.get("has_sub_layer"):
                    specialist_dets = res.get("specialist_detections", [])
                    # Validação estrita de sobcamada: exige componente estrutural chave na RoI
                    if any(k in cname_lower for k in ["extintor", "babcock", "walker", "yamato", "fire"]):
                        has_core_component = any(
                            any(core in d.get("class_name", "").lower() for core in ["handle", "gauge_good", "safety pin", "safety_pin"])
                            for d in specialist_dets
                        )
                        if not has_core_component:
                            logger.info("⚠️ [Tempo Real] Falso positivo descartado para '%s' (conf: %.2f) sem componentes estruturais na sobcamada.", cname, b_item.get("confidence", 0))
                            continue

                    b_item["sub_layer"] = res
                    sub_layer_results.append({
                        "object_class": cname,
                        "is_conforming": res["is_conforming"],
                        "passed_items": res["passed_items"],
                        "failed_items": res["failed_items"],
                        "alerts": res["alerts"]
                    })
                valid_boxes.append(b_item)

        all_detection_boxes = valid_boxes
        global_class_counts = defaultdict(int)
        for b in all_detection_boxes:
            global_class_counts[b["class_name"]] += 1

        has_primary_objects = len(all_detection_boxes) > 0

        if not has_primary_objects:
            compliance_result = {
                "status": "SEM OBJETOS",
                "alerts": ["Nenhum objeto detectado com o limiar de confiança definido."],
                "report": {"recognized": [], "missing": [], "errors": []}
            }
            compliance_report = None
        else:
            if disable_compliance:
                compliance_result = {
                    "status": "DISABLED",
                    "alerts": []
                }
            else:
                compliance_result = compliance_service.evaluate(
                    all_detection_boxes, image_width=w, image_height=h
                )
                for res_item in sub_layer_results:
                    for alert in res_item.get("alerts", []):
                        if alert not in compliance_result["alerts"]:
                            compliance_result["alerts"].append(alert)
                            compliance_result["status"] = "NÃO CONFORME"

            # Gerar laudo IA (Ollama) APENAS quando objetos forem encontrados e validados pela sobcamada
            compliance_report = None
            if not disable_compliance and settings.ENABLE_PERSONALIZED_MESSAGE and global_class_counts:
                from app.services.ollama_message_service import ollama_message_service
                analysis_dict = {
                    "class_counts": dict(global_class_counts),
                    "compliance_status": compliance_result["status"],
                    "compliance_alerts": compliance_result["alerts"],
                    "sub_layer_analysis": sub_layer_results
                }
                compliance_report = ollama_message_service.generate_personalized_message(
                    analysis_dict, model_name or "all"
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
            "requested_model": model_name or "all",
            "class_counts": dict(global_class_counts),
            "boxes": all_detection_boxes,
            "compliance_status": compliance_result["status"],
            "compliance_alerts": compliance_result["alerts"],
            "compliance_report": compliance_report,
            "sub_layer_analysis": sub_layer_results
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
            if compliance_status in ("NAO_CONFORME", "NÃO CONFORME"):
                h, w = img.shape[:2]
                banner_h = max(50, int(h * 0.08))
                overlay = img.copy()
                cv2.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 255), -1)
                img = cv2.addWeighted(overlay, 0.7, img, 0.3, 0)

                alert_text = "ALERTA: NAO CONFORMIDADE!"
                alerts_str = " ".join(compliance_alerts or [])
                if "placa" in alerts_str.lower() and "ausente no suporte" in alerts_str.lower():
                    alert_text = "ALERTA: PLACA DE SINALIZACAO AUSENTE!"
                elif "extintor" in alerts_str.lower() or "extinguidor" in alerts_str.lower():
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
            if "placa" in alerts_str.lower() and "ausente no suporte" in alerts_str.lower():
                alert_text = "ALERTA: PLACA DE SINALIZACAO AUSENTE!"
            elif "extintor" in alerts_str.lower() or "extinguidor" in alerts_str.lower():
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
                if compliance_status in ("NAO_CONFORME", "NÃO CONFORME"):
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

        # Detectar imagens AVIF / HEIC antes das assinaturas ftyp de MP4
        if len(header) >= 12 and header[4:8] == b"ftyp" and header[8:12] in (b"avif", b"avis", b"mif1", b"heic", b"heix"):
            return "AVIF"

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

detection_service = DetectionService()