"""
Pydantic schemas for Ground Truth request data and Live Evaluation Metrics.
"""
# pylint: disable=too-few-public-methods
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MetricBox(BaseModel):
    """Schema representing a bounding box for metric calculations."""
    class_name: str = Field(..., description="Nome da classe")
    x1: float = Field(..., description="Coordenada x1")
    y1: float = Field(..., description="Coordenada y1")
    x2: float = Field(..., description="Coordenada x2")
    y2: float = Field(..., description="Coordenada y2")
    confidence: Optional[float] = Field(None, description="Confianca (predicoes)")


class GroundTruthRequest(BaseModel):
    """Schema representing a request to submit ground truth bounding boxes."""
    sample_id: str = Field(..., description="ID da amostra retornado em /detection/analyze")
    model_name: Optional[str] = Field(
        None, description="Obrigatorio quando nao houver predicao pendente"
    )
    boxes: List[MetricBox] = Field(default_factory=list, description="Boxes de ground truth")


class LiveMetricsResponse(BaseModel):
    """Schema representing the calculated evaluation metrics (precision, recall, mAP)."""
    window_seconds: int
    samples_evaluated: int
    pending_samples: int
    precision: float
    recall: float
    mAP50: float
    mAP50_95: float
    per_class: Dict[str, Dict[str, float | int]]
    totals: Dict[str, int]

