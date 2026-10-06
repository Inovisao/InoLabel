"""Pré-anotação por modelo (detecção e rastreamento)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TrackingInferenceRequest(BaseModel):
    session_id: Optional[str] = None
    frame_indices: Optional[List[int]] = None
    save_annotations: bool = True
    frame_rate: int = 30
    confidence_threshold: Optional[float] = None

    @field_validator("frame_rate")
    @classmethod
    def frame_rate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("frame_rate deve ser maior que zero.")
        return value

    @field_validator("confidence_threshold")
    @classmethod
    def optional_confidence_threshold_in_range(
        cls, value: Optional[float]
    ) -> Optional[float]:
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("confidence_threshold deve estar entre 0.0 e 1.0.")
        return value

class TrackingDetectionResult(BaseModel):
    bbox: List[float]
    class_id: int
    class_name: str
    confidence: float
    track_id: int

class TrackingFrameResult(BaseModel):
    frame_index: int
    timestamp: float
    detections: List[TrackingDetectionResult] = Field(default_factory=list)

class TrackingInferenceResponse(BaseModel):
    mode: str = "tracking"
    session_id: str
    processed_frames: int
    saved_annotations: bool
    frames: List[TrackingFrameResult] = Field(default_factory=list)
