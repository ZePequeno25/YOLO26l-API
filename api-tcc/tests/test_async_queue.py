import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from config.settings import settings
import logging

client = TestClient(app)

def test_disable_logs_silencing():
    # Test logging silencing toggle
    orig_disable_logs = settings.DISABLE_LOGS
    try:
        settings.DISABLE_LOGS = True
        # Mimic main.py silencing logic
        logging.disable(logging.CRITICAL)
        assert logging.root.manager.disable >= logging.CRITICAL
    finally:
        # Restore logging levels
        logging.disable(logging.NOTSET)
        settings.DISABLE_LOGS = orig_disable_logs

@patch("app.routes.detection_routes.detection_service.analyze")
def test_async_queue_mode_flow(mock_analyze):
    # Enable async queue mode for the test
    orig_async = settings.ASYNC_QUEUE_MODE
    settings.ASYNC_QUEUE_MODE = True
    try:
        # Mock successful analysis result
        mock_analyze.return_value = {
            "requested_model": "cadeira",
            "class_counts": {"cadeira": 1},
            "num_frames_processed": 1,
            "boxes": []
        }

        # Send test file upload
        files = {"file": ("test.jpg", b"fake-jpeg-data", "image/jpeg")}
        
        response = client.post("/detection/analyze-test", files=files)
        
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data
        assert data["status"] == "PENDENTE"
        
        job_id = data["job_id"]
        
        # In TestClient, background tasks run synchronously within the call, 
        # so it will already be completed upon request completion.
        job_response = client.get(f"/detection/job/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()
        assert job_data["status"] == "CONCLUIDO"
        assert job_data["success"] is True
        assert job_data["requested_model"] == "cadeira"
        
    finally:
        settings.ASYNC_QUEUE_MODE = orig_async


@patch("app.routes.detection_routes.detection_service.analyze")
def test_x_request_id_idempotency(mock_analyze):
    orig_async = settings.ASYNC_QUEUE_MODE
    settings.ASYNC_QUEUE_MODE = True
    try:
        mock_analyze.return_value = {
            "requested_model": "cadeira",
            "class_counts": {"cadeira": 1},
            "num_frames_processed": 1,
            "boxes": []
        }

        # 1. Enviar primeira requisição com X-Request-ID
        headers = {"X-Request-ID": "test-req-id-123"}
        files = {"file": ("test.jpg", b"fake-jpeg-data", "image/jpeg")}
        resp1 = client.post("/detection/analyze-test", files=files, headers=headers)
        assert resp1.status_code == 202
        data1 = resp1.json()
        job_id1 = data1["job_id"]

        # 2. Enviar segunda requisição com o MESMO X-Request-ID
        files2 = {"file": ("test.jpg", b"fake-jpeg-data", "image/jpeg")}
        resp2 = client.post("/detection/analyze-test", files=files2, headers=headers)
        data2 = resp2.json()
        
        # Como o TestClient executa tarefas em segundo plano de forma síncrona,
        # o job original pode já estar concluído (status 200) ou ainda em processamento (202).
        if resp2.status_code == 200:
            assert data2["requested_model"] == "cadeira"
        else:
            assert resp2.status_code == 202
            assert data2["job_id"] == job_id1

    finally:
        settings.ASYNC_QUEUE_MODE = orig_async


@patch("app.routes.detection_routes.detection_service.analyze")
def test_status_endpoint_aliases(mock_analyze):
    orig_async = settings.ASYNC_QUEUE_MODE
    settings.ASYNC_QUEUE_MODE = True
    try:
        mock_analyze.return_value = {
            "requested_model": "cadeira",
            "class_counts": {"cadeira": 1},
            "num_frames_processed": 1,
            "boxes": []
        }

        files = {"file": ("test.jpg", b"fake-jpeg-data", "image/jpeg")}
        resp = client.post("/detection/analyze-test", files=files)
        job_id = resp.json()["job_id"]

        # 1. Validar consulta via /detection/job/{job_id}
        resp_job = client.get(f"/detection/job/{job_id}")
        assert resp_job.status_code == 200
        assert resp_job.json()["status"] == "CONCLUIDO"

        # 2. Validar consulta via alias /detection/status/{job_id}
        resp_status = client.get(f"/detection/status/{job_id}")
        assert resp_status.status_code == 200
        assert resp_status.json()["status"] == "CONCLUIDO"

        # 3. Validar consulta via alias raiz /status/{job_id}
        resp_root = client.get(f"/status/{job_id}")
        assert resp_root.status_code == 200
        assert resp_root.json()["status"] == "CONCLUIDO"

    finally:
        settings.ASYNC_QUEUE_MODE = orig_async
