"""
Unit tests for the ComplianceService.
Tests spatial alignment, semantic fusion, and temporal video consensus.
"""
from app.services.compliance_service import ComplianceService


def test_compliance_empty():
    service = ComplianceService()
    result = service.evaluate([])
    assert result["status"] == "CONFORME"
    assert len(result["alerts"]) == 0


def test_compliance_fire_conforme():
    service = ComplianceService()
    # Placa na posição (100, 100, 200, 150)
    # Extintor diretamente abaixo na posição (100, 300, 200, 500)
    boxes = [
        {
            "frame_index": 0,
            "class_name": "sinal de parque",
            "confidence": 0.95,
            "x1": 100,
            "y1": 100,
            "x2": 200,
            "y2": 150
        },
        {
            "frame_index": 0,
            "class_name": "co2 portátil",
            "confidence": 0.98,
            "x1": 100,
            "y1": 300,
            "x2": 200,
            "y2": 500
        }
    ]
    result = service.evaluate(boxes)
    assert result["status"] == "CONFORME"
    assert len(result["alerts"]) == 0
    assert "extintor de incêndio" not in result["report"]["missing"]


def test_compliance_fire_missing_extinguisher():
    service = ComplianceService()
    # Placa presente, extintor totalmente ausente da cena
    boxes = [
        {
            "frame_index": 0,
            "class_name": "placa_extintor",
            "confidence": 0.95,
            "x1": 100,
            "y1": 100,
            "x2": 200,
            "y2": 150
        }
    ]
    result = service.evaluate(boxes)
    assert result["status"] == "NAO_CONFORME"
    assert len(result["alerts"]) == 1
    assert "extintor de incêndio" in result["report"]["missing"]
    assert len(result["report"]["errors"]) == 1
    assert result["report"]["errors"][0]["rule"] == "Segurança contra Incêndio"


def test_compliance_fire_misaligned():
    service = ComplianceService()
    # Placa na esquerda e extintor na extrema direita (desalinhados)
    boxes = [
        {
            "frame_index": 0,
            "class_name": "sinal de parque",
            "confidence": 0.95,
            "x1": 100,
            "y1": 100,
            "x2": 200,
            "y2": 150
        },
        {
            "frame_index": 0,
            "class_name": "extintor",
            "confidence": 0.98,
            "x1": 1500,
            "y1": 300,
            "x2": 1600,
            "y2": 500
        }
    ]
    # Usando largura de imagem padrão de 1920
    result = service.evaluate(boxes, image_width=1920, image_height=1080)
    assert result["status"] == "NAO_CONFORME"
    assert "extintor de incêndio" in result["report"]["missing"]


def test_compliance_epi_violation():
    service = ComplianceService()
    # Pessoa e caixa de "sem luvas"
    boxes = [
        {
            "frame_index": 0,
            "class_name": "pessoa",
            "confidence": 0.90,
            "x1": 200,
            "y1": 200,
            "x2": 400,
            "y2": 800
        },
        {
            "frame_index": 0,
            "class_name": "sem luvas",
            "confidence": 0.88,
            "x1": 220,
            "y1": 500,
            "x2": 280,
            "y2": 560
        }
    ]
    result = service.evaluate(boxes)
    assert result["status"] == "NAO_CONFORME"
    assert "luvas" in result["report"]["missing"]
    assert len(result["report"]["errors"]) == 1
    assert result["report"]["errors"][0]["rule"] == "Uso Obrigatório de EPI"


def test_compliance_temporal_consensus_conforme():
    service = ComplianceService()
    # Vídeo de 4 frames:
    # Frame 0: Placa sem extintor (dropout do extintor - 1 falha)
    # Frame 1: Placa com extintor (conforme)
    # Frame 2: Placa com extintor (conforme)
    # Frame 3: Placa com extintor (conforme)
    # Taxa de falhas = 1/4 = 25% (<= 30% limite), deve ser considerado CONFORME.
    boxes = [
        # Frame 0
        {"frame_index": 0, "class_name": "placa", "confidence": 0.9, "x1": 100, "y1": 100, "x2": 200, "y2": 150, "track_id": 1},
        # Frame 1
        {"frame_index": 1, "class_name": "placa", "confidence": 0.9, "x1": 100, "y1": 100, "x2": 200, "y2": 150, "track_id": 1},
        {"frame_index": 1, "class_name": "extintor", "confidence": 0.9, "x1": 100, "y1": 300, "x2": 200, "y2": 500, "track_id": 2},
        # Frame 2
        {"frame_index": 2, "class_name": "placa", "confidence": 0.9, "x1": 100, "y1": 100, "x2": 200, "y2": 150, "track_id": 1},
        {"frame_index": 2, "class_name": "extintor", "confidence": 0.9, "x1": 100, "y1": 300, "x2": 200, "y2": 500, "track_id": 2},
        # Frame 3
        {"frame_index": 3, "class_name": "placa", "confidence": 0.9, "x1": 100, "y1": 100, "x2": 200, "y2": 150, "track_id": 1},
        {"frame_index": 3, "class_name": "extintor", "confidence": 0.9, "x1": 100, "y1": 300, "x2": 200, "y2": 500, "track_id": 2},
    ]
    result = service.evaluate(boxes)
    assert result["status"] == "CONFORME"
    assert len(result["alerts"]) == 0


def test_compliance_temporal_consensus_nao_conforme():
    service = ComplianceService()
    # Vídeo de 4 frames:
    # Frame 0: Placa sem extintor (falha)
    # Frame 1: Placa sem extintor (falha)
    # Frame 2: Placa com extintor (conforme)
    # Frame 3: Placa sem extintor (falha)
    # Taxa de falhas = 3/4 = 75% (> 30% limite), deve ser considerado NAO_CONFORME.
    boxes = [
        # Frame 0
        {"frame_index": 0, "class_name": "placa", "confidence": 0.9, "x1": 100, "y1": 100, "x2": 200, "y2": 150, "track_id": 1},
        # Frame 1
        {"frame_index": 1, "class_name": "placa", "confidence": 0.9, "x1": 100, "y1": 100, "x2": 200, "y2": 150, "track_id": 1},
        # Frame 2
        {"frame_index": 2, "class_name": "placa", "confidence": 0.9, "x1": 100, "y1": 100, "x2": 200, "y2": 150, "track_id": 1},
        {"frame_index": 2, "class_name": "extintor", "confidence": 0.9, "x1": 100, "y1": 300, "x2": 200, "y2": 500, "track_id": 2},
        # Frame 3
        {"frame_index": 3, "class_name": "placa", "confidence": 0.9, "x1": 100, "y1": 100, "x2": 200, "y2": 150, "track_id": 1},
    ]
    result = service.evaluate(boxes)
    assert result["status"] == "NAO_CONFORME"
    assert "extintor de incêndio" in result["report"]["missing"]
