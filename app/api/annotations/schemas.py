"""Criação e edição de anotações."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.api.common.schemas import OBBGeometry


class AnnotationUpsert(BaseModel):
    category_id: int
    # No modo keypoint a bbox é calculada a partir dos pontos (pode ir [0, 0, 0, 0]).
    bbox: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    obb: Optional[OBBGeometry] = None
    track_id: Optional[int] = None
    source: str = "manual"
    score: Optional[float] = None
    keypoints: Optional[List[List[float]]] = None

    @field_validator("category_id")
    @classmethod
    def category_id_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError(
                f"category_id deve ser >= 0 (índice da classe YOLO), recebeu {value}."
            )
        return value

    @field_validator("bbox")
    @classmethod
    def bbox_must_have_four_elements(cls, value: List[float]) -> List[float]:
        if len(value) != 4:
            raise ValueError(
                f"bbox deve ter exatamente 4 elementos [x, y, w, h], recebeu {len(value)}."
            )
        return value

class ReviewedUpdate(BaseModel):
    """Marca a imagem como revisada sem objetos (entra no dataset como negativo)."""

    reviewed: bool = True

class FrameReviewState(BaseModel):
    image_id: int
    reviewed: bool
    annotation_count: int

class AnnotationPatch(BaseModel):
    """Campos alteráveis de uma anotação; os omitidos ficam como estão.

    ``track_id: null`` explícito remove o ID (o campo omitido não mexe nele).
    """

    category_id: Optional[int] = None
    track_id: Optional[int] = None
    bbox: Optional[List[float]] = None
    obb: Optional[OBBGeometry] = None
    keypoints: Optional[List[List[float]]] = None

class NextTrackId(BaseModel):
    next_track_id: int
