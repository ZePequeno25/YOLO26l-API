import pytest

from app.services.detection_service import DetectionService


def test_validate_model_name_accepts_safe_identifiers():
    assert DetectionService._validate_model_name("chair") == "chair"
    assert DetectionService._validate_model_name("model_01") == "model_01"
    assert DetectionService._validate_model_name("model-01") == "model-01"


@pytest.mark.parametrize(
    "invalid_name",
    ["", "   ", "../secret", "..\\secret", "model/name", "model.name", "a" * 200],
)
def test_validate_model_name_rejects_unsafe_values(invalid_name):
    with pytest.raises(ValueError):
        DetectionService._validate_model_name(invalid_name)
