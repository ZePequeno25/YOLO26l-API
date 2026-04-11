import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.core.request_protection as request_protection_module
import app.routes.auth_routes as auth_routes
import app.routes.detection_routes as detection_routes
from app.core.firebase import TokenValidationError
from app.core.not_found_guard import NotFoundGuard
from app.core.request_protection import RequestProtectionMiddleware
from app.core.analysis_guard import analysis_guard
from config.settings import settings
from main import app


@pytest.fixture(autouse=True)
def clear_analysis_guard_state():
    analysis_guard._active_users.clear()
    yield
    analysis_guard._active_users.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_system_route_returns_not_found_without_auth(client: TestClient):
    response = client.get("/system/status")

    assert response.status_code == 404


def test_system_route_returns_not_found_for_non_admin(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    monkeypatch.setattr(
        request_protection_module,
        "verify_id_token",
        lambda token: {"uid": "user-1", "admin": False},
    )

    response = client.get("/system/status", headers={"Authorization": "Bearer token"})

    assert response.status_code == 404


def test_system_route_allows_admin(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    monkeypatch.setattr(
        request_protection_module,
        "verify_id_token",
        lambda token: {"uid": "admin-1", "admin": True},
    )

    response = client.get("/system/status", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_download_requires_valid_authentication(client: TestClient):
    response = client.get("/detection/download/test.txt")

    assert response.status_code == 404


def test_download_returns_file_for_admin(monkeypatch: pytest.MonkeyPatch, tmp_path, client: TestClient):
    download_file = tmp_path / "test.txt"
    download_file.write_text("conteudo protegido", encoding="utf-8")

    monkeypatch.setattr(
        request_protection_module,
        "verify_id_token",
        lambda token: {"uid": "admin-1", "admin": True, "email": "admin@test.local"},
    )
    monkeypatch.setattr(
        detection_routes,
        "verify_id_token",
        lambda token: {"uid": "admin-1", "admin": True, "email": "admin@test.local"},
    )
    monkeypatch.setattr(detection_routes.detection_service, "output_dir", tmp_path)

    response = client.get("/detection/download/test.txt", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.content == b"conteudo protegido"


def test_not_found_guard_blocks_burst_after_threshold(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "NOT_FOUND_MAX_HITS", 4)
    monkeypatch.setattr(settings, "NOT_FOUND_WINDOW_SECONDS", 1)
    monkeypatch.setattr(settings, "NOT_FOUND_BLOCK_SECONDS", 30)

    local_app = FastAPI()
    local_app.add_middleware(NotFoundGuard)

    with TestClient(local_app) as local_client:
        statuses = [local_client.get("/missing").status_code for _ in range(5)]

    assert statuses[:4] == [404, 404, 404, 404]
    assert statuses[4] == 403


def test_request_protection_rate_limit_blocks_burst(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT_MAX", 2)
    monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT_WINDOW", 10)
    monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT_BLOCK", 30)

    local_app = FastAPI()
    local_app.add_middleware(RequestProtectionMiddleware)

    @local_app.get("/ping")
    async def ping():
        return {"ok": True}

    with TestClient(local_app) as local_client:
        statuses = [local_client.get("/ping").status_code for _ in range(3)]

    assert statuses == [200, 200, 429]


def test_test_token_hidden_when_debug_disabled(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    monkeypatch.setattr(settings, "DEBUG", False)

    response = client.get("/auth/test-token")

    assert response.status_code == 404


def test_concurrent_analysis_allows_only_one_request_per_user(monkeypatch: pytest.MonkeyPatch):
    async def fake_analyze(file, model):
        await asyncio.sleep(0.2)
        return {
            "class_counts": {"chair": 1},
            "num_frames_processed": 1,
            "detected_chairs": 1,
            "frames_with_detections": 1,
            "boxes": [],
            "analysis_model_used": "chair",
            "message": "ok",
            "analyzed_file": None,
            "analyzed_output": None,
        }

    monkeypatch.setattr(
        detection_routes,
        "verify_id_token",
        lambda token: {"uid": "same-user", "email": "user@test.local"},
    )
    monkeypatch.setattr(detection_routes.detection_service, "analyze", fake_analyze)
    monkeypatch.setattr(
        detection_routes.ollama_message_service,
        "generate_personalized_message",
        lambda result, model_name: "Formalmente encontrou 1 cadeira.",
    )
    monkeypatch.setattr(detection_routes.live_metrics_service, "add_prediction_sample", lambda **kwargs: None)

    barrier = Barrier(2)

    def send_request() -> int:
        with TestClient(app) as local_client:
            barrier.wait()
            response = local_client.post(
                "/detection/analyze",
                headers={"Authorization": "Bearer token"},
                files={"file": ("image.jpg", b"fake-image", "image/jpeg")},
                data={"model": "chair"},
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: send_request(), range(2)))

    assert sorted(statuses) == [200, 429]


def test_system_route_invalid_token_still_returns_not_found(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    def raise_invalid(token: str):
        raise TokenValidationError("token invalido")

    monkeypatch.setattr(request_protection_module, "verify_id_token", raise_invalid)

    response = client.get("/system/status", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 404


def test_auth_token_requires_app_check_when_enabled(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    monkeypatch.setattr(settings, "ENABLE_APP_CHECK", True)

    def raise_app_check(_: str):
        raise TokenValidationError("App Check invalido")

    monkeypatch.setattr(auth_routes, "_verify_app_check", raise_app_check)

    response = client.post("/auth/token", data={"id_token": "firebase-token"})

    assert response.status_code == 401
    assert "App Check" in response.json()["detail"]


def test_auth_token_accepts_valid_app_check(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    monkeypatch.setattr(settings, "ENABLE_APP_CHECK", True)
    monkeypatch.setattr(auth_routes, "_verify_app_check", lambda token: {"sub": "app"})
    monkeypatch.setattr(
        auth_routes,
        "verify_id_token",
        lambda token: {"uid": "user-1", "email": "user@test.local", "name": "User", "email_verified": True},
    )
    monkeypatch.setattr(
        auth_routes,
        "generate_api_token",
        lambda **kwargs: {"access_token": "api-token", "token_type": "Bearer", "expires_in": 86400},
    )

    response = client.post(
        "/auth/token",
        data={"id_token": "firebase-token"},
        headers={"X-Firebase-AppCheck": "valid-app-check"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "api-token"


def test_auth_token_accepts_json_payload(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    monkeypatch.setattr(settings, "ENABLE_APP_CHECK", False)
    monkeypatch.setattr(
        auth_routes,
        "verify_id_token",
        lambda token: {"uid": "user-json", "email": "json@test.local", "name": "Json User", "email_verified": True},
    )
    monkeypatch.setattr(
        auth_routes,
        "generate_api_token",
        lambda **kwargs: {"access_token": "json-api-token", "token_type": "Bearer", "expires_in": 86400},
    )

    response = client.post("/auth/token", json={"id_token": "firebase-json-token"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "json-api-token"


def test_oversized_upload_is_blocked_before_analysis(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    monkeypatch.setattr(settings, "MAX_REQUEST_BODY_BYTES", 10)

    response = client.post(
        "/detection/analyze",
        headers={"Authorization": "Bearer token"},
        files={"file": ("image.jpg", b"0123456789abcdef", "image/jpeg")},
        data={"model": "chair"},
    )

    assert response.status_code == 413


def test_analysis_accepts_access_token_form_alias(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    async def fake_analyze(file, model):
        return {
            "class_counts": {"chair": 1},
            "num_frames_processed": 1,
            "detected_chairs": 1,
            "frames_with_detections": 1,
            "boxes": [],
            "analysis_model_used": "chair",
            "message": "ok",
            "analyzed_file": None,
            "analyzed_output": None,
        }

    monkeypatch.setattr(
        detection_routes,
        "verify_id_token",
        lambda value: {"uid": "alias-user", "email": "alias@test.local"},
    )
    monkeypatch.setattr(detection_routes.detection_service, "analyze", fake_analyze)
    monkeypatch.setattr(
        detection_routes.ollama_message_service,
        "generate_personalized_message",
        lambda result, model_name: "Formalmente encontrou 1 cadeira.",
    )
    monkeypatch.setattr(detection_routes.live_metrics_service, "add_prediction_sample", lambda **kwargs: None)

    response = client.post(
        "/detection/analyze",
        files={"file": ("image.jpg", b"fake-image", "image/jpeg")},
        data={"model": "chair", "access_token": "alias-token"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_analysis_accepts_double_bearer_in_authorization(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    async def fake_analyze(file, model):
        return {
            "class_counts": {"chair": 1},
            "num_frames_processed": 1,
            "detected_chairs": 1,
            "frames_with_detections": 1,
            "boxes": [],
            "analysis_model_used": "chair",
            "message": "ok",
            "analyzed_file": None,
            "analyzed_output": None,
        }

    monkeypatch.setattr(
        detection_routes,
        "verify_id_token",
        lambda value: {"uid": "double-bearer-user", "email": "user@test.local"},
    )
    monkeypatch.setattr(detection_routes.detection_service, "analyze", fake_analyze)
    monkeypatch.setattr(
        detection_routes.ollama_message_service,
        "generate_personalized_message",
        lambda result, model_name: "Formalmente encontrou 1 cadeira.",
    )
    monkeypatch.setattr(detection_routes.live_metrics_service, "add_prediction_sample", lambda **kwargs: None)

    response = client.post(
        "/detection/analyze",
        headers={"Authorization": "Bearer Bearer \"token-android\""},
        files={"file": ("image.jpg", b"fake-image", "image/jpeg")},
        data={"model": "chair"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_invalid_host_is_rejected():
    with TestClient(app) as local_client:
        response = local_client.get("/auth/test-token", headers={"Host": "evil.example.com"})

    assert response.status_code == 400


def test_security_headers_are_present_on_responses(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    monkeypatch.setattr(
        request_protection_module,
        "verify_id_token",
        lambda token: {"uid": "admin-1", "admin": True},
    )

    response = client.get("/system/status", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]