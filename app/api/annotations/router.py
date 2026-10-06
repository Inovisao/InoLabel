"""Rotas HTTP das anotações. Só traduz a requisição para o serviço."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.api.annotations import service
from app.api.annotations.schemas import (
    AnnotationPatch,
    AnnotationUpsert,
    FrameReviewState,
    NextTrackId,
    ReviewedUpdate,
)
from app.api.common.schemas import Annotation

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


@router.get("/debug")
def debug_store() -> dict:
    return service.debug_store()


# Antes de /{image_id}: senão "next-track-id" seria lido como image_id.
@router.get("/next-track-id", response_model=NextTrackId)
def next_track_id() -> NextTrackId:
    return service.next_track_id()


@router.get("/{image_id}", response_model=List[Annotation])
def get_annotations(image_id: int) -> List[Annotation]:
    return service.get_annotations(image_id)


@router.post("/{image_id}", response_model=Annotation)
def add_annotation(image_id: int, body: AnnotationUpsert) -> Annotation:
    return service.add_annotation(image_id, body)


@router.post("/{image_id}/reviewed", response_model=FrameReviewState)
def set_reviewed(image_id: int, body: ReviewedUpdate) -> FrameReviewState:
    return service.set_reviewed(image_id, body)


@router.patch("/{image_id}/{ann_id}", response_model=Annotation)
def update_annotation(image_id: int, ann_id: int, body: AnnotationPatch) -> Annotation:
    return service.update_annotation(image_id, ann_id, body)


@router.delete("/{image_id}/{ann_id}")
def delete_annotation(image_id: int, ann_id: int) -> dict:
    return service.delete_annotation(image_id, ann_id)


@router.delete("/{image_id}")
def clear_annotations(image_id: int) -> dict:
    return service.clear_annotations(image_id)
