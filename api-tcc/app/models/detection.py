"""
Pydantic schemas for object detection results and metrics.
"""
# pylint: disable=too-few-public-methods
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DetectionBox(BaseModel):
    """Schema representing a single detected bounding box in a video frame."""
    frame_index: int
    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    track_id: Optional[int] = None
    model_source: Optional[str] = None


class AnalyzedFileInfo(BaseModel):
    """Schema representing details of the analyzed output file."""
    path: str
    filename: str
    download_url: str


class AnalysisResponse(BaseModel):
    """Schema representing the complete analysis response payload."""
    success: bool
    message: str
    personalized_message: Optional[str] = None
    analysis_model_used: Optional[str] = None
    requested_model: Optional[str] = None
    llm_model_used: Optional[str] = None
    class_counts: Dict[str, int]
    num_frames_processed: int
    evaluation_sample_id: Optional[str] = None
    detected_chairs: int = 0
    frames_with_detections: Optional[int] = None
    analyzed_file: Optional[str] = None
    analyzed_output: Optional[AnalyzedFileInfo] = None
    boxes: Optional[List[DetectionBox]] = None
    compliance_status: Optional[str] = None
    compliance_alerts: Optional[List[str]] = None
    compliance_report: Optional[Dict[str, Any]] = None

