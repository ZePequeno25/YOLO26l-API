from pydantic import BaseModel
from typing import Dict, Optional, List


class DetectionBox(BaseModel):
    frame_index: int
    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    track_id: Optional[int] = None


class AnalyzedFileInfo(BaseModel):
    path: str
    filename: str
    download_url: str

class AnalysisResponse(BaseModel):
    success: bool
    message: str
    personalized_message: Optional[str] = None
    analysis_model_used: Optional[str] = None
    llm_model_used: Optional[str] = None
    class_counts: Dict[str, int]
    num_frames_processed: int
    evaluation_sample_id: Optional[str] = None
    detected_chairs: int = 0
    frames_with_detections: Optional[int] = None
    analyzed_file: Optional[str] = None
    analyzed_output: Optional[AnalyzedFileInfo] = None
    boxes: Optional[List[DetectionBox]] = None