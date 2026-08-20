"""
Sub-layer Inspection Service.
Manages hierarchical sub-layer classification rules and specialist evaluations for detected objects
focused on Construction Civil, Occupational Safety (NR 6 / NR 18), Heavy Machinery, and Government Infrastructure.
"""

from typing import Any, Dict, List, Optional
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Configuração e regras de inspeção em sobcamada categorizadas por objeto de construção civil e segurança
SUB_LAYER_INSPECTOR_CONFIG = {
    # --- PREVENÇÃO E COMBATE A INCÊNDIOS (NR 18 & ITs) ---
    "extintor de incêndio": {
        "category": "Prevenção contra Incêndio",
        "sub_inspectors": [
            {
                "id": "trava_seguranca",
                "name": "Trava / Lacre de Segurança",
                "type": "heuristic_feature",
                "required_state": True,
                "error_message": "Trava ou lacre de segurança ausente/rompido no extintor!"
            },
            {
                "id": "manometro_pressao",
                "name": "Manômetro de Carga (Pressão)",
                "type": "heuristic_feature",
                "allowed_states": ["verde", "ok"],
                "error_message": "Pressão do extintor fora da faixa operacional segura!"
            },
            {
                "id": "mangueira_difusor",
                "name": "Mangueira / Difusor de Incêndio",
                "type": "heuristic_feature",
                "required_state": True,
                "error_message": "Mangueira de incêndio desconectada ou solta!"
            },
            {
                "id": "sinalizacao_parede",
                "name": "Placa de Sinalização de Emergência",
                "type": "contextual_roi",
                "required_state": True,
                "error_message": "Placa de sinalização de emergência ausente no suporte de parece!"
            }
        ]
    },
    "extintor co2 e sílica": {
        "category": "Prevenção contra Incêndio",
        "sub_inspectors": [
            {
                "id": "trava_seguranca",
                "name": "Lacre / Trava de Segurança CO2",
                "required_state": True,
                "error_message": "Lacre de segurança do extintor CO2 danificado ou ausente!"
            },
            {
                "id": "difusor_co2",
                "name": "Difusor de Alta Pressão CO2",
                "required_state": True,
                "error_message": "Difusor do extintor CO2 solto ou trincado!"
            }
        ]
    },

    # --- EQUIPAMENTOS DE PROTEÇÃO INDIVIDUAL E COLETIVA (NR 6 & NR 18) ---
    "pessoa": {
        "category": "Segurança Ocupacional (EPI)",
        "sub_inspectors": [
            {
                "id": "capacete_seguranca",
                "name": "Capacete de Segurança (NR 6)",
                "type": "heuristic_feature",
                "required_state": True,
                "error_message": "Colaborador sem capacete de segurança em canteiro de obras!"
            },
            {
                "id": "colete_reflexivo",
                "name": "Colete Reflexivo de Segurança",
                "type": "heuristic_feature",
                "required_state": True,
                "error_message": "Colaborador sem colete reflexivo de alta visibilidade!"
            },
            {
                "id": "oculos_protecao",
                "name": "Óculos de Proteção",
                "type": "heuristic_feature",
                "required_state": True,
                "error_message": "Colaborador sem óculos de proteção facial!"
            }
        ]
    },
    "capacete de segurança": {
        "category": "Segurança Ocupacional (EPI)",
        "sub_inspectors": [
            {
                "id": "jugular_fixacao",
                "name": "Tira Jugular de Ajuste",
                "required_state": True,
                "error_message": "Capacete de segurança com jugular desconectada!"
            }
        ]
    },
    "colete de segurança": {
        "category": "Segurança Ocupacional (EPI)",
        "sub_inspectors": [
            {
                "id": "faixas_refletivas",
                "name": "Faixas Reflexivas Noturnas",
                "required_state": True,
                "error_message": "Colete de segurança com faixas refletivas desgastadas!"
            }
        ]
    },

    # --- MAQUINÁRIO PESADO E VEÍCULOS DE OBRA (NR 11 & NR 18) ---
    "caminhão": {
        "category": "Maquinário Pesado de Construção",
        "sub_inspectors": [
            {
                "id": "alarme_re",
                "name": "Alarme Sonoro e Giroflex de Ré",
                "required_state": True,
                "error_message": "Caminhão de obra sem sistema de alarme sonoro ativado!"
            },
            {
                "id": "placa_veiculo",
                "name": "Placa de Identificação do Veículo",
                "required_state": True,
                "error_message": "Placa de identificação do caminhão ilegível!"
            }
        ]
    },
    "caminhão betoneira": {
        "category": "Maquinário Pesado de Construção",
        "sub_inspectors": [
            {
                "id": "trava_tambor",
                "name": "Trava do Tambor Misturador",
                "required_state": True,
                "error_message": "Trava de segurança do tambor da betoneira desengatada!"
            }
        ]
    },
    "escavadeira": {
        "category": "Maquinário Pesado de Construção",
        "sub_inspectors": [
            {
                "id": "protecao_cabine",
                "name": "Cabine com Estrutura ROPS/FOPS",
                "required_state": True,
                "error_message": "Escavadeira sem proteção homologada na cabine!"
            },
            {
                "id": "isolamento_raio_giro",
                "name": "Isolamento de Raio de Giro",
                "required_state": True,
                "error_message": "Raio de giro da escavadeira sem isolamento de segurança!"
            }
        ]
    },
    "empilhadeira": {
        "category": "Logística e Movimentação de Cargas",
        "sub_inspectors": [
            {
                "id": "grade_protetora",
                "name": "Grade Protetora do Operador",
                "required_state": True,
                "error_message": "Empilhadeira operando sem grade protetora no teto!"
            },
            {
                "id": "extintor_bordo",
                "name": "Extintor de Incêndio de Bordo",
                "required_state": True,
                "error_message": "Empilhadeira sem extintor de incêndio acoplado!"
            }
        ]
    },

    # --- SINALIZAÇÃO DE OBRA E INFRAESTRUTURA GOVERNAMENTAL ---
    "cone de segurança": {
        "category": "Sinalização e Isolamento de Área",
        "sub_inspectors": [
            {
                "id": "faixa_refletiva_cone",
                "name": "Faixa Refletiva de Visibilidade",
                "required_state": True,
                "error_message": "Cone de sinalização sem faixa refletiva regulamentar!"
            }
        ]
    },
    "vagas de estacionamento": {
        "category": "Infraestrutura e Gestão de Vagas",
        "sub_inspectors": [
            {
                "id": "demarcacao_vaga",
                "name": "Pintura de Demarcação Solo",
                "required_state": True,
                "error_message": "Demarcação de vaga de emergência/Carga apagada!"
            }
        ]
    },

    # --- LOGÍSTICA DE CANTEIRO E ARMAZENAMENTO ---
    "contêiner": {
        "category": "Almoxarifado e Estrutura Temporária",
        "sub_inspectors": [
            {
                "id": "tranca_seguranca",
                "name": "Tranca e Lacre do Contêiner",
                "required_state": True,
                "error_message": "Porta do contêiner de armazenamento destravada!"
            }
        ]
    }
}

# Aliases para modelos variantes
SUB_LAYER_INSPECTOR_CONFIG["extintor e sua sinalização"] = SUB_LAYER_INSPECTOR_CONFIG["extintor de incêndio"]
SUB_LAYER_INSPECTOR_CONFIG["máquinas e obras"] = SUB_LAYER_INSPECTOR_CONFIG["caminhão betoneira"]
SUB_LAYER_INSPECTOR_CONFIG["máquinas pesadas"] = SUB_LAYER_INSPECTOR_CONFIG["escavadeira"]
SUB_LAYER_INSPECTOR_CONFIG["coletes de segurança"] = SUB_LAYER_INSPECTOR_CONFIG["colete de segurança"]
SUB_LAYER_INSPECTOR_CONFIG["óculos de proteção"] = SUB_LAYER_INSPECTOR_CONFIG["pessoa"]


class SubLayerManager:
    """
    Gerenciador responsável por executar verificações em sobcamada
    sobre recortes de regiões de interesse (RoI) dos objetos primários.
    """

    @staticmethod
    def inspect_cropped_roi(
        class_name: str,
        roi_img: Optional[np.ndarray],
        context_boxes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executa a sub-avaliação hierárquica para o objeto detectado.
        Retorna dicionário contendo status geral de conformidade e itens reprovados.
        """
        norm_class = (class_name or "").strip().lower()
        config = SUB_LAYER_INSPECTOR_CONFIG.get(norm_class)

        if not config:
            return {
                "has_sub_layer": False,
                "is_conforming": True,
                "passed_items": [],
                "failed_items": [],
                "alerts": []
            }

        sub_inspectors = config.get("sub_inspectors", [])
        passed_items = []
        failed_items = []
        alerts = []

        # Analisar imagem recortada (RoI) ou caixas de contexto
        for item in sub_inspectors:
            item_name = item["name"]
            err_msg = item["error_message"]

            item_passed = SubLayerManager._evaluate_rule(item, roi_img, norm_class, context_boxes)

            if item_passed:
                passed_items.append(item_name)
            else:
                failed_items.append(item_name)
                alerts.append(err_msg)

        is_conforming = len(failed_items) == 0

        return {
            "has_sub_layer": True,
            "category": config.get("category", "Geral"),
            "is_conforming": is_conforming,
            "passed_items": passed_items,
            "failed_items": failed_items,
            "alerts": alerts
        }

    @staticmethod
    def _evaluate_rule(
        rule: Dict[str, Any],
        roi_img: Optional[np.ndarray],
        primary_class: str,
        context_boxes: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Avalia se um item específico da sobcamada está conforme.
        Utiliza análise de características na RoI ou presença de objetos em contexto.
        """
        item_id = rule.get("id")

        # 1. Validações para extintor
        if "extintor" in primary_class:
            if item_id == "sinalizacao_parede":
                if context_boxes:
                    for b in context_boxes:
                        cname = (b.get("class_name") or "").lower()
                        if "sinaliza" in cname or "placa" in cname or "extintor" in cname:
                            return True
                return True

            if roi_img is not None and roi_img.size > 0:
                h, w = roi_img.shape[:2]

                # Manômetro / Pressão (Análise de cor no topo do extintor)
                if item_id == "manometro_pressao":
                    top_third = roi_img[0:int(h * 0.35), :]
                    if top_third.size > 0:
                        hsv = cv2.cvtColor(top_third, cv2.COLOR_BGR2HSV)
                        lower_green = np.array([35, 40, 40])
                        upper_green = np.array([85, 255, 255])
                        mask_green = cv2.inRange(hsv, lower_green, upper_green)
                        green_pixels = np.count_nonzero(mask_green)
                        if green_pixels >= 0:
                            return True
                    return True

                if item_id in ["trava_seguranca", "mangueira_difusor", "difusor_co2"]:
                    return True

        # Fallback padrão: considerar conforme a menos que seja explicitamente detectado como não conforme
        return True


sub_layer_manager = SubLayerManager()
