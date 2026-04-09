from concurrent.futures import ThreadPoolExecutor
from typing import Any

from _pytest.monkeypatch import MonkeyPatch

from app.services.ollama_message_service import OllamaMessageService


class DummyCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "Mensagem local", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_run_success(*args: Any, **kwargs: Any) -> DummyCompletedProcess:
    return DummyCompletedProcess(returncode=0, stdout="Analise concluida com sucesso", stderr="")


def _fake_run_failure(*args: Any, **kwargs: Any) -> DummyCompletedProcess:
    return DummyCompletedProcess(returncode=1, stdout="", stderr="erro")


def test_generate_personalized_message_concurrent_success(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("app.services.ollama_message_service.subprocess.run", _fake_run_success)
    service = OllamaMessageService()

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
    assert all("Analise" in msg for msg in results)


def test_generate_personalized_message_concurrent_fallback(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("app.services.ollama_message_service.subprocess.run", _fake_run_failure)
    service = OllamaMessageService()

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
    assert all("modelo 'chair'" in msg for msg in results)
