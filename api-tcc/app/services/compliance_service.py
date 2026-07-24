"""
Compliance service module.
Evaluates YOLO object detection bounding boxes against safety regulations
(e.g., fire extinguishers paired with signs, and proper usage of EPIs).
"""
import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Service class that runs logical checks on detected objects to verify compliance.
    """
    def __init__(self):
        # Mapeamento semântico de sinalização de extintores
        self.sign_classes: Set[str] = {
            "placa", "sinal", "sinalizacao", "sinalização", "placa_extintor",
            "sinal_extintor", "fire_extinguisher_sign", "sinal de parque"
        }

        # Mapeamento semântico de extintores de incêndio
        self.fire_classes: Set[str] = {
            "extintor", "extinguidor", "extintor_de_incendio", "extintor de incêndio",
            "co2 portátil", "mc 2a co2", "mf 60 sílica", "ya 10nx"
        }

        # Mapeamento de violações de EPI
        self.epi_violation_classes: Dict[str, str] = {
            "sem luvas": "luvas",
            "sem óculos de proteção": "óculos de proteção",
            "sem capuz de segurança": "capuz de segurança",
            "sem vestuário de segurança": "vestuário de segurança",
            "sem colete de segurança": "colete de segurança",
            "sem capacete de segurança": "capacete de segurança",
            "sem máscara": "máscara"
        }

    def evaluate(
        self,
        boxes: List[Dict[str, Any]],
        image_width: int = 1920,
        image_height: int = 1080
    ) -> Dict[str, Any]:
        """
        Avalia as caixas detectadas contra as regras de conformidade regulamentar.
        
        Suporta imagens individuais e sequências temporais de vídeo.
        """
        if not boxes:
            return {
                "status": "CONFORME",
                "alerts": [],
                "report": {"recognized": [], "missing": [], "errors": []}
            }

        # Garantir dimensões mínimas para evitar divisão por zero
        image_width = max(image_width, 100)
        image_height = max(image_height, 100)

        # 1. Agrupar boxes por frame
        boxes_by_frame = {}
        for box in boxes:
            f_idx = box.get("frame_index", 0)
            if f_idx not in boxes_by_frame:
                boxes_by_frame[f_idx] = []
            boxes_by_frame[f_idx].append(box)

        status = "CONFORME"
        alerts = []
        recognized_objects = []
        missing_objects = []
        errors = []

        # Para rastreamento temporal em vídeos
        sign_temporal_history = {}  # key: track_id ou coordenada_aproximada -> list of compliance status (bool)
        sign_to_box_map = {}       # key: track_id ou coordenada_aproximada -> box representation
        
        # 2. Avaliar conformidade quadro a quadro
        for frame_idx, frame_boxes in sorted(boxes_by_frame.items()):
            # Filtrar objetos por tipo semântico
            signs = []
            extinguishers = []
            epi_violations = []
            people = []

            for box in frame_boxes:
                cls_lower = box["class_name"].lower()
                
                # Identificar placas
                is_sign = cls_lower in self.sign_classes or any(s in cls_lower for s in ["placa", "sinalizac"])
                if is_sign:
                    signs.append(box)
                    recognized_objects.append({
                        "class_name": box["class_name"],
                        "confidence": box["confidence"],
                        "frame_index": frame_idx,
                        "position": {"x1": box["x1"], "y1": box["y1"], "x2": box["x2"], "y2": box["y2"]}
                    })

                # Identificar extintores
                is_ext = cls_lower in self.fire_classes or any(e in cls_lower for e in ["extintor", "extinguidor"])
                if is_ext:
                    extinguishers.append(box)
                    recognized_objects.append({
                        "class_name": box["class_name"],
                        "confidence": box["confidence"],
                        "frame_index": frame_idx,
                        "position": {"x1": box["x1"], "y1": box["y1"], "x2": box["x2"], "y2": box["y2"]}
                    })

                # Identificar violações de EPI
                if cls_lower in self.epi_violation_classes:
                    epi_violations.append(box)

                # Identificar pessoas
                if cls_lower == "pessoa":
                    people.append(box)
                    recognized_objects.append({
                        "class_name": "pessoa",
                        "confidence": box["confidence"],
                        "frame_index": frame_idx,
                        "position": {"x1": box["x1"], "y1": box["y1"], "x2": box["x2"], "y2": box["y2"]}
                    })

            # --- REGRA 1: Associação Espacial Placa vs Extintor ---
            for sign in signs:
                x1_s, y1_s, x2_s, y2_s = sign["x1"], sign["y1"], sign["x2"], sign["y2"]
                cx_s = (x1_s + x2_s) / 2
                cy_s = (y1_s + y2_s) / 2
                w_s = x2_s - x1_s
                h_s = y2_s - y1_s

                # Identificar placa de forma única (usando track_id se houver, senão chave espacial)
                sign_key = sign.get("track_id")
                if sign_key is None:
                    # Chave espacial aproximada para agrupar entre frames (grade de 50px)
                    sign_key = f"sign_{int(cx_s // 50)}_{int(cy_s // 50)}"

                if sign_key not in sign_temporal_history:
                    sign_temporal_history[sign_key] = []
                sign_to_box_map[sign_key] = sign

                # Verificar se há algum extintor espacialmente associado (alinhado abaixo)
                has_associated_extinguisher = False
                for ext in extinguishers:
                    x1_e, y1_e, x2_e, y2_e = ext["x1"], ext["y1"], ext["x2"], ext["y2"]
                    cx_e = (x1_e + x2_e) / 2
                    cy_e = (y1_e + y2_e) / 2
                    w_e = x2_e - x1_e

                    # Condições espaciais:
                    # 1. O extintor deve estar abaixo da placa no eixo vertical (cy_e > cy_s)
                    # 2. O desalinhamento horizontal deve ser menor que 2.0 * largura da placa ou 15% da largura da imagem
                    horizontal_tolerance = max(2.0 * w_s, 2.0 * w_e, 0.15 * image_width, 150)
                    is_below = cy_e > cy_s
                    is_aligned_horizontally = abs(cx_s - cx_e) < horizontal_tolerance
                    
                    # Evitar emparelhar se estiver excessivamente longe (ex: mais que 70% da altura da imagem)
                    is_within_vertical_limit = (y1_e - y2_s) < (0.7 * image_height)

                    if is_below and is_aligned_horizontally and is_within_vertical_limit:
                        has_associated_extinguisher = True
                        break

                sign_temporal_history[sign_key].append(has_associated_extinguisher)

            # --- REGRA 2: Não Conformidade de EPI ---
            for violation in epi_violations:
                missing_epi = self.epi_violation_classes[violation["class_name"].lower()]
                error_desc = f"Não conformidade de EPI detectada: '{violation['class_name']}' no frame {frame_idx}."
                status = "NAO_CONFORME"
                alerts.append(error_desc)
                missing_objects.append(missing_epi)
                errors.append({
                    "rule": "Uso Obrigatório de EPI",
                    "description": error_desc,
                    "frame_index": frame_idx,
                    "trigger_object": violation["class_name"],
                    "trigger_position": {
                        "x1": violation["x1"],
                        "y1": violation["y1"],
                        "x2": violation["x2"],
                        "y2": violation["y2"]
                    },
                    "missing_object": missing_epi
                })

        # 3. Consolidar conformidade de sinalização com Suavização Temporal (Consenso)
        # Em vídeos (múltiplos frames), aplicamos o consenso temporal para evitar falsos alarmes rápidos.
        # Em imagens estáticas (1 frame), se estiver ausente, já alerta imediatamente.
        is_video = len(boxes_by_frame) > 1

        for sign_key, history in sign_temporal_history.items():
            sign = sign_to_box_map[sign_key]
            
            # Se for vídeo, exige que esteja sem extintor em mais de 30% das aparições
            # Se for imagem, basta estar ausente em uma aparição (100%)
            total_appearances = len(history)
            failures = history.count(False)
            failure_rate = failures / total_appearances if total_appearances > 0 else 0.0

            threshold = 0.3 if is_video else 0.0
            
            if failure_rate > threshold:
                status = "NAO_CONFORME"
                error_desc = (
                    f"Placa de sinalização '{sign['class_name']}' encontrada, "
                    f"mas o extintor regulamentar correspondente está ausente."
                )
                alerts.append(error_desc)
                missing_objects.append("extintor de incêndio")
                errors.append({
                    "rule": "Segurança contra Incêndio",
                    "description": error_desc,
                    "frame_index": sign.get("frame_index", 0),
                    "trigger_object": sign["class_name"],
                    "trigger_position": {
                        "x1": sign["x1"],
                        "y1": sign["y1"],
                        "x2": sign["x2"],
                        "y2": sign["y2"]
                    },
                    "missing_object": "extintor de incêndio"
                })

        # Evitar duplicados
        missing_objects = sorted(list(set(missing_objects)))
        alerts = sorted(list(set(alerts)))

        # Garantir consistência nas respostas de reconhecimentos duplicados
        unique_recognized = []
        seen = set()
        for obj in recognized_objects:
            seen_key = (obj["class_name"], obj["frame_index"], obj["position"]["x1"], obj["position"]["y1"])
            if seen_key not in seen:
                seen.add(seen_key)
                unique_recognized.append(obj)

        return {
            "status": status,
            "alerts": alerts,
            "report": {
                "recognized": unique_recognized,
                "missing": missing_objects,
                "errors": errors
            }
        }


compliance_service = ComplianceService()
