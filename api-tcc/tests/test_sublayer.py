"""
Unit tests for SubLayerManager (Classificação em Sobcamada).
"""
import numpy as np
import pytest
from app.services.sublayer_service import SubLayerManager


def test_sublayer_extintor_conforming():
    # ROI sintetizada (imagem verde no topo para manometro)
    roi = np.zeros((100, 100, 3), dtype=np.uint8)
    roi[0:30, :] = [0, 255, 0]  # Verde

    context_boxes = [{"class_name": "Placa de Sinalização"}]
    res = SubLayerManager.inspect_cropped_roi("extintor de incêndio", roi, context_boxes)

    assert res["has_sub_layer"] is True
    assert res["is_conforming"] is True
    assert len(res["failed_items"]) == 0


def test_sublayer_non_conforming_class_without_sublayer():
    res = SubLayerManager.inspect_cropped_roi("cadeira", None, None)
    assert res["has_sub_layer"] is False
    assert res["is_conforming"] is True


def test_sublayer_pessoa_inspection():
    res = SubLayerManager.inspect_cropped_roi("pessoa", None, None)
    assert res["has_sub_layer"] is True
    assert res["is_conforming"] is True
