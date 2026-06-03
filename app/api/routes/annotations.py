from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from app.api.schemas import Annotation, AnnotationUpsert

router = APIRouter(prefix="/api/annotations", tags=["annotations"])

# image_id → list of annotations
_store: Dict[int, List[Annotation]] = {}
_next_id: int = 1


def reset_annotations() -> None:
    global _next_id
    _store.clear()
    _next_id = 1


@router.get("/{image_id}", response_model=List[Annotation])
def get_annotations(image_id: int) -> List[Annotation]:
    return _store.get(image_id, [])


@router.post("/{image_id}", response_model=Annotation)
def add_annotation(image_id: int, body: AnnotationUpsert) -> Annotation:
    global _next_id
    ann = Annotation(
        id=_next_id,
        image_id=image_id,
        category_id=body.category_id,
        bbox=body.bbox,
        track_id=body.track_id,
        source=body.source,
    )
    _store.setdefault(image_id, []).append(ann)
    _next_id += 1
    return ann


@router.delete("/{image_id}/{ann_id}")
def delete_annotation(image_id: int, ann_id: int) -> dict:
    annotations = _store.get(image_id, [])
    before = len(annotations)
    _store[image_id] = [a for a in annotations if a.id != ann_id]
    if len(_store[image_id]) == before:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return {"ok": True}


@router.delete("/{image_id}")
def clear_annotations(image_id: int) -> dict:
    _store.pop(image_id, None)
    return {"ok": True}
