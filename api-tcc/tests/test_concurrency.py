import pytest
from fastapi.testclient import TestClient
from main import app
from config.settings import settings
from unittest.mock import patch
from pathlib import Path
import shutil

client = TestClient(app)

def test_error_report_robustness_and_absolute_path():
    # Test error reporting with missing optional fields
    payload = {
        "screen": "CrashActivity",
        "app_version": "2.0.0"
    }
    
    # Clean up logs directory if any
    errors_dir = Path(__file__).resolve().parent.parent / "logs" / "errors"
    if errors_dir.exists():
        try:
            shutil.rmtree(errors_dir)
        except Exception:
            pass
        
    response = client.post("/errors/report", json=payload)
    
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    
    # Assert logs directory exists under the absolute path
    assert errors_dir.exists()
    
    # Assert a log file for 'unknown' was created
    unknown_dir = errors_dir / "unknown"
    assert unknown_dir.exists()
    
    log_files = list(unknown_dir.glob("*.log"))
    assert len(log_files) > 0

def test_pending_jobs_queue_limit_backpressure():
    # Lower queue limit for testing
    orig_limit = settings.MAX_PENDING_JOBS
    orig_async = settings.ASYNC_QUEUE_MODE
    settings.MAX_PENDING_JOBS = 1
    settings.ASYNC_QUEUE_MODE = True
    
    # Access detection service jobs directly
    from app.routes.detection_routes import detection_service
    # Clear current jobs
    detection_service.jobs.clear()
    
    try:
        # Create an active job to fill the queue
        detection_service.create_job("job-active-1")
        
        # Next upload request should be rejected with 429
        files = {"file": ("test.jpg", b"fake-data", "image/jpeg")}
        response = client.post("/detection/analyze-test", files=files)
        
        assert response.status_code == 429
        data = response.json()
        assert "cheia" in data["detail"]
    finally:
        settings.MAX_PENDING_JOBS = orig_limit
        settings.ASYNC_QUEUE_MODE = orig_async
        detection_service.jobs.clear()

def test_lru_job_cleanup():
    # Lower retention limit for testing
    orig_retention = settings.JOB_RETENTION_LIMIT
    settings.JOB_RETENTION_LIMIT = 2
    
    from app.routes.detection_routes import detection_service
    detection_service.jobs.clear()
    
    try:
        # Create jobs
        detection_service.create_job("job-1")
        detection_service.update_job_status("job-1", "CONCLUIDO", result={"data": 1})
        
        detection_service.create_job("job-2")
        detection_service.update_job_status("job-2", "CONCLUIDO", result={"data": 2})
        
        # Creating a 3rd job should trigger LRU pruning since we are at settings.JOB_RETENTION_LIMIT (2)
        # and job-1 is finished.
        detection_service.create_job("job-3")
        
        # job-1 should have been deleted, but job-2 and job-3 remain
        assert "job-1" not in detection_service.jobs
        assert "job-2" in detection_service.jobs
        assert "job-3" in detection_service.jobs
    finally:
        settings.JOB_RETENTION_LIMIT = orig_retention
        detection_service.jobs.clear()

def test_error_report_malformed_json_fallback():
    # Test error reporting with invalid malformed JSON
    payload = "{"
    
    response = client.post(
        "/errors/report",
        content=payload,
        headers={"content-type": "application/json"}
    )
    
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    
    # Assert logs folder has 'unknown' folder with log
    errors_dir = Path(__file__).resolve().parent.parent / "logs" / "errors"
    unknown_dir = errors_dir / "unknown"
    assert unknown_dir.exists()
    
    log_files = list(unknown_dir.glob("*.log"))
    assert len(log_files) > 0
