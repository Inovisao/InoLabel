from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from app.api import state as _state
from app.api.schemas import Annotation, AnnotationUpsert

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/annotations", tags=["annotations"])

# All annotation data lives in _state.annotation_store (shared with frames.py)
# _state.next_ann_id[0] is the next annotation id counter


def reset_annotations() -> None:
    _state.annotation_store.clear()
    _state.next_ann_id[0] = 1


def _autosave(image_id: int) -> None:
    """Write YOLO txt for this frame. Failures are logged and never surface as HTTP errors."""
    try:
        session = _state.active_session()
        if session is None:
            return
        if not _state.frame_paths or image_id >= len(_state.frame_paths):
            return
        dims = _state.frame_dims.get(image_id)
        if dims is None:
            log.warning("autosave: dims not known for frame %d — skipped", image_id)
            return

        img_w, img_h = dims
        if img_w == 0 or img_h == 0:
            return

        path = _state.frame_paths[image_id]
        annotations: List[Annotation] = _state.annotation_store.get(image_id, [])

        labels_dir = session.output_path / "labels"
        labels_dir.mkdir(parents=True, exist_ok=True)
        txt_path = labels_dir / (path.stem + ".txt")

        lines: List[str] = []
        for ann in annotations:
            x, y, w, h = ann.bbox
            x = max(0.0, x)
            y = max(0.0, y)
            w = min(w, img_w - x)
            h = min(h, img_h - y)
            if w <= 0 or h <= 0:
                continue
            cx = (x + w / 2) / img_w
            cy = (y + h / 2) / img_h
            wn = w / img_w
            hn = h / img_h
            lines.append(f"{ann.category_id} {cx:.6f} {cy:.6f} {wn:.6f} {hn:.6f}")

        txt_path.write_text("\n".join(lines) + ("\n" if lines else ""))
        log.debug("autosave: %d annotations → %s", len(lines), txt_path)

    except Exception:
        log.exception("autosave failed for frame %d", image_id)


def _load_frame_from_txt(
    image_id: int, path: Path, img_w: int, img_h: int, output_path: Path
) -> None:
    """Load YOLO annotations from disk into annotation_store (resume mode)."""
    labels_dir = output_path / "labels"
    txt_path = labels_dir / (path.stem + ".txt")
    if not txt_path.exists():
        return

    anns: List[Annotation] = []
    try:
        for line in txt_path.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            cls_id = int(parts[0])
            cx, cy, wn, hn = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            w = wn * img_w
            h = hn * img_h
            x = cx * img_w - w / 2
            y = cy * img_h - h / 2
            anns.append(Annotation(
                id=_state.next_ann_id[0],
                image_id=image_id,
                category_id=cls_id,
                bbox=[x, y, w, h],
                source="file",
            ))
            _state.next_ann_id[0] += 1
    except Exception:
        log.exception("Failed to load %s", txt_path)
        return

    if anns:
        _state.annotation_store[image_id] = anns
        log.debug("loaded %d annotations from %s", len(anns), txt_path)


@router.get("/debug")
def debug_store() -> dict:
    """Development helper — returns raw annotation_store contents."""
    return {
        "total_frames_with_annotations": len(_state.annotation_store),
        "frame_indices": list(_state.annotation_store.keys()),
        "counts": {k: len(v) for k, v in _state.annotation_store.items()},
        "next_id": _state.next_ann_id[0],
    }


@router.get("/{image_id}", response_model=List[Annotation])
def get_annotations(image_id: int) -> List[Annotation]:
    return _state.annotation_store.get(image_id, [])


@router.post("/{image_id}", response_model=Annotation)
def add_annotation(image_id: int, body: AnnotationUpsert) -> Annotation:
    ann = Annotation(
        id=_state.next_ann_id[0],
        image_id=image_id,
        category_id=body.category_id,
        bbox=body.bbox,
        track_id=body.track_id,
        source=body.source,
    )
    _state.annotation_store.setdefault(image_id, []).append(ann)
    _state.next_ann_id[0] += 1
    _autosave(image_id)
    return ann


@router.delete("/{image_id}/{ann_id}")
def delete_annotation(image_id: int, ann_id: int) -> dict:
    anns = _state.annotation_store.get(image_id, [])
    before = len(anns)
    _state.annotation_store[image_id] = [a for a in anns if a.id != ann_id]
    if len(_state.annotation_store[image_id]) == before:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    _autosave(image_id)
    return {"ok": True}


@router.delete("/{image_id}")
def clear_annotations(image_id: int) -> dict:
    _state.annotation_store.pop(image_id, None)
    _autosave(image_id)
    return {"ok": True}
