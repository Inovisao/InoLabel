"""Rotas HTTP do modo classificação (sob /api/annotations/{image_id}/classification).

Registrado antes do router de anotações: senão DELETE /{image_id}/classification
cairia em DELETE /{image_id}/{ann_id}.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.classification import service
from app.api.classification.schemas import ClassificationResult, ClassificationState, ClassificationUpsert

router = APIRouter(prefix="/api/annotations", tags=["classification"])


@router.post("/{image_id}/classification", response_model=ClassificationResult)
def classify_frame(image_id: int, body: ClassificationUpsert) -> ClassificationResult:
    return service.classify_frame(image_id, body)


@router.get("/{image_id}/classification", response_model=ClassificationState)
def get_classification(image_id: int) -> ClassificationState:
    return service.get_classification(image_id)


@router.delete("/{image_id}/classification", response_model=ClassificationState)
def undo_classification(image_id: int) -> ClassificationState:
    return service.undo_classification(image_id)
