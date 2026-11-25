from concurrent.futures import ThreadPoolExecutor
from typing import Any

from _pytest.monkeypatch import MonkeyPatch

from app.services.ollama_message_service import OllamaMessageService


class DummyCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "Mensagem local", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_http_success(*args: Any, **kwargs: Any) -> str:
    return "Analise concluida com sucesso"


def _fake_http_failure(*args: Any, **kwargs: Any) -> None:
    return None


def test_generate_personalized_message_concurrent_success(monkeypatch: MonkeyPatch):
    service = OllamaMessageService()
    monkeypatch.setattr(service, "_call_ollama_http", _fake_http_success)

    payload: dict[str, Any] = {
        "class_counts": {"chair": 2},
        "num_frames_processed": 10,
        "frames_with_detections": 3,
        "detected_chairs": 2,
    }

    def work(_: int) -> str:
        return service.generate_personalized_message(payload, "chair")

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(work, range(200)))

    assert len(results) == 200
    assert all("Analise concluida com sucesso" in msg for msg in results)


def test_generate_personalized_message_concurrent_fallback(monkeypatch: MonkeyPatch):
    service = OllamaMessageService()
    monkeypatch.setattr(service, "_call_ollama_http", _fake_http_failure)

    payload: dict[str, Any] = {
        "class_counts": {"chair": 0},
        "num_frames_processed": 4,
        "frames_with_detections": 0,
        "detected_chairs": 0,
    }

    def work(_: int) -> str:
        return service.generate_personalized_message(payload, "chair")

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(work, range(200)))

    assert len(results) == 200
    assert all("Nenhum objeto detectado na cena com o limiar definido." == msg for msg in results)


def test_fallback_treats_cadeira_and_chair_as_same_object():
    payload: dict[str, Any] = {
        "class_counts": {"chair": 2},
    }

    message = OllamaMessageService._build_fallback_message(payload, "cadeira")

    assert message == "A análise identificou 2 chair. Status: Conforme."


def test_fallback_reports_different_object_with_detectou_typo_fixed():
    payload: dict[str, Any] = {
        "class_counts": {"door": 1},
    }

    message = OllamaMessageService._build_fallback_message(payload, "cadeira")

    assert message == "A análise identificou 1 door. Status: Conforme."
