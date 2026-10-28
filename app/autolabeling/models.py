"""Provider-independent contracts for box labeling and review."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    adapter: str = 'ultralytics'
    model_id: Optional[str] = None
    model_path: str = ''
    confidence: float = Field(default=0.4, ge=0, le=1, allow_inf_nan=False)
    class_mapping: Dict[str, Optional[str]] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_inputs(self):
        from app.autolabeling.model_catalog.registry import definition_for
        from app.api.common.errors import InvalidInput
        try:
            definition = definition_for(self.model_id or self.adapter)
        except InvalidInput as exc:
            raise ValueError(str(exc)) from exc
        if definition.adapter != self.adapter:
            raise ValueError('The model and adapter do not match.')
        self.model_path = self.model_path.strip()
        if definition.source == 'imported' and not self.model_path:
            raise ValueError('Choose a local model checkpoint.')
        self.parameters = definition.inputs.model_validate(self.parameters).model_dump()
        return self


class RunRequest(BaseModel):
    session_id: str
    config: ModelConfig
    frame_indices: Optional[List[int]] = None


class Proposal(BaseModel):
    id: str
    frame_index: int
    category_id: int = Field(ge=0)
    class_name: str
    bbox: List[float] = Field(min_length=4, max_length=4)
    score: Optional[float] = Field(default=None, allow_inf_nan=False)
    score_type: str = 'detection_confidence'
    prompt: Optional[str] = None
    status: Literal['pending', 'accepted', 'rejected'] = 'pending'
    annotation_id: Optional[int] = None
    accepted_bbox: Optional[List[float]] = None
    accepted_category_id: Optional[int] = None

    @field_validator('bbox')
    @classmethod
    def valid_box(cls, value):
        import math
        if not all(math.isfinite(x) for x in value) or value[2] <= 0 or value[3] <= 0:
            raise ValueError('A proposal requires a finite box with positive dimensions.')
        return value


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
