import numpy as np
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@patch("app.routes.detection_routes.cv2.VideoCapture")
@patch("app.routes.detection_routes.detection_service.analyze_frame")
def test_stream_route_success(mock_analyze_frame, mock_video_capture):
    # Mock VideoCapture behaviour
    mock_cap = MagicMock()
    # isOpened will return True twice, then False to terminate the loop
    mock_cap.isOpened.side_effect = [True, True, False]
    
    # Mock reading a frame successfully
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cap.read.return_value = (True, dummy_frame)
    mock_video_capture.return_value = mock_cap

    # Mock analyze_frame output
    mock_analyze_frame.return_value = {
        "class_counts": {"pessoa": 1},
        "boxes": [{
            "frame_index": 0,
            "class_id": 0,
            "class_name": "pessoa",
            "confidence": 0.95,
            "x1": 10,
            "y1": 10,
            "x2": 50,
            "y2": 50
        }],
        "compliance_status": "CONFORME",
        "compliance_alerts": []
    }

    response = client.get("/detection/stream?video_source=mock_video.mp4&frame_stride=1")
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # Validate event data format and content
    content = response.text
    assert "data:" in content
    assert "pessoa" in content
    assert "CONFORME" in content
    mock_cap.release.assert_called_once()
