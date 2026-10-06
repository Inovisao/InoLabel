"""Tipos compartilhados entre funcionalidades: modo da tarefa e a anotação."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, field_validator


class TaskMode(str, Enum):
    TRACKING = "tracking"
    DETECTION = "detection"
    OBB = "obb"
    CLASSIFICATION = "classification"
    KEYPOINT = "keypoint"

class OBBGeometry(BaseModel):
    cx: float
    cy: float
    width: float
    height: float
    angle: float = 0.0
    angle_unit: str = "degrees"
    points: Optional[List[List[float]]] = None

    @field_validator("width", "height")
    @classmethod
    def positive_size(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("width e height devem ser maiores que zero.")
        return value

    @field_validator("angle_unit")
    @classmethod
    def angle_unit_degrees(cls, value: str) -> str:
        if value != "degrees":
            raise ValueError("angle_unit deve ser 'degrees'.")
        return value

    @field_validator("points")
    @classmethod
    def points_must_be_four_xy_pairs(
        cls, value: Optional[List[List[float]]]
    ) -> Optional[List[List[float]]]:
        if value is None:
            return value
        if len(value) != 4 or any(len(point) != 2 for point in value):
            raise ValueError("points deve conter exatamente 4 pares [x, y].")
        return value

class Annotation(BaseModel):
    id: int
    image_id: int
    category_id: int
    bbox: List[float]
    obb: Optional[OBBGeometry] = None
    track_id: Optional[int] = None
    source: str = "manual"
    score: Optional[float] = None
    # Modo keypoint: [[x, y, v], ...] na ordem da classe; v = 0 ausente, 1 oculto, 2 visível.
    keypoints: Optional[List[List[float]]] = None
