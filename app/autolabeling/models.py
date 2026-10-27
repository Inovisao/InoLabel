"""Provider-independent contracts for box labeling and review."""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    adapter: Literal['ultralytics'] = 'ultralytics'
    model_path: str
    confidence: float = Field(default=0.4, ge=0, le=1, allow_inf_nan=False)
    class_mapping: Dict[str, Optional[str]] = Field(default_factory=dict)

    @field_validator('model_path')
    @classmethod
    def nonempty_path(cls, value):
        if not value.strip():
            raise ValueError('Choose a local model checkpoint.')
        return value.strip()


class RunRequest(BaseModel):
    session_id: str
    config: ModelConfig
    frame_indices: Optional[List[int]] = None


class Proposal(BaseModel):
    id: str
    frame_index: int
    category_id: int
    class_name: str
    bbox: List[float]
    score: Optional[float] = None
    status: Literal['pending', 'accepted', 'rejected'] = 'pending'
    annotation_id: Optional[int] = None
    accepted_bbox: Optional[List[float]] = None
    accepted_category_id: Optional[int] = None


class ReviewRequest(BaseModel):
    proposal_id: str
    bbox: Optional[List[float]] = Field(default=None, min_length=4, max_length=4)
    category_id: Optional[int] = Field(default=None, ge=0)

    @field_validator('bbox')
    @classmethod
    def finite_geometry(cls, value):
        import math
        if value is not None and not all(math.isfinite(x) for x in value):
            raise ValueError('Coordinates must be finite.')
        return value
