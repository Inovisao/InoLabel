from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from app.api import state as _state
from app.api.schemas import (
    Annotation,
    AnnotationUpsert,
    ClassificationResult,
    ClassificationUpsert,
    OBBGeometry,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/annotations", tags=["annotations"])

# All annotation data lives in _state.annotation_store (shared with frames.py)
# _state.next_ann_id[0] is the next annotation id counter

# Tracks which labels/ directories have already been created this session,
# avoiding a redundant mkdir syscall on every autosave.
_labels_dir_created: set[str] = set()


def reset_annotations() -> None:
    _state.annotation_store.clear()
    _state.next_ann_id[0] = 1
    _labels_dir_created.clear()


def _points_from_obb(obb: OBBGeometry) -> list[list[float]]:
    theta = math.radians(float(obb.angle))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    half_w = float(obb.width) / 2.0
    half_h = float(obb.height) / 2.0
    local = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)]
    return [
        [float(obb.cx + dx * cos_t - dy * sin_t), float(obb.cy + dx * sin_t + dy * cos_t)]
        for dx, dy in local
    ]


def _obb_from_bbox(bbox: list[float]) -> OBBGeometry:
    x, y, w, h = (float(value) for value in bbox)
    obb = OBBGeometry(
        cx=x + w / 2.0,
        cy=y + h / 2.0,
        width=w,
        height=h,
        angle=0.0,
        angle_unit="degrees",
    )
    obb.points = _points_from_obb(obb)
    return obb


def _obb_from_points(points: list[list[float]]) -> OBBGeometry:
    p0, p1, p2, p3 = points
    cx = sum(point[0] for point in points) / 4.0
    cy = sum(point[1] for point in points) / 4.0
    width = math.dist(p0, p1)
    height = math.dist(p1, p2)
    angle = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    return OBBGeometry(
        cx=cx,
        cy=cy,
        width=width,
        height=height,
        angle=angle,
        angle_unit="degrees",
        points=points,
    )


def _autosave(image_id: int) -> None:
    """Write YOLO txt for this frame. Failures are logged and never surface as HTTP errors."""
    try:
        import cv2 as _cv2

        session = _state.active_session()
        if session is None:
            return
        if not _state.frame_paths or image_id >= len(_state.frame_paths):
            return
        dims = _state.frame_dims.get(image_id)
        if dims is None:
            # Frame not yet loaded through the UI — read dims from disk so we never
            # silently discard annotations added before the frame is displayed.
            img_path = _state.frame_paths[image_id]
            img = _cv2.imread(str(img_path))
            if img is None:
                log.warning("autosave: cannot read image %s for frame %d — skipped", img_path.name, image_id)
                return
            h, w = img.shape[:2]
            dims = (w, h)
            _state.frame_dims[image_id] = dims

        img_w, img_h = dims
        if img_w == 0 or img_h == 0:
            return

        path = _state.frame_paths[image_id]
        annotations: List[Annotation] = _state.annotation_store.get(image_id, [])

        labels_dir = session.output_path / "labels"
        labels_key = str(labels_dir)
        if labels_key not in _labels_dir_created:
            labels_dir.mkdir(parents=True, exist_ok=True)
            _labels_dir_created.add(labels_key)
        txt_path = labels_dir / (path.stem + ".txt")

        lines: List[str] = []
        for ann in annotations:
            if session.mode == "obb" and ann.obb is not None:
                points = ann.obb.points or _points_from_obb(ann.obb)
                values = [str(ann.category_id)]
                for px, py in points:
                    values.append(f"{max(0.0, min(1.0, float(px) / img_w)):.6f}")
                    values.append(f"{max(0.0, min(1.0, float(py) / img_h)):.6f}")
                lines.append(" ".join(values))
                continue

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
    """Load YOLO annotations from disk into annotation_store for a single frame."""
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
            obb = None
            if len(parts) >= 9:
                points = [
                    [float(parts[i]) * img_w, float(parts[i + 1]) * img_h]
                    for i in range(1, 9, 2)
                ]
                obb = _obb_from_points(points)
                x = min(point[0] for point in points)
                y = min(point[1] for point in points)
                w = max(point[0] for point in points) - x
                h = max(point[1] for point in points) - y
            else:
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
                obb=obb,
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
    # Use frame_paths when available (fully loaded session); fall back to
    # session.total_frames so the guard works before any frame is fetched.
    session = _state.active_session()
    total = len(_state.frame_paths) or (session.total_frames if session else 0)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessao ativa nao encontrada.")
    if session.mode == "classification":
        raise HTTPException(
            status_code=422,
            detail="Classificacao nao usa bounding boxes; use /annotations/{image_id}/classification.",
        )
    if session.mode == "detection" and body.track_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Modo deteccao padrao nao aceita track_id.",
        )
    if session.mode == "tracking" and body.source == "model" and body.track_id is None:
        raise HTTPException(
            status_code=422,
            detail="Modo rastreamento exige track_id para anotacoes geradas pelo modelo.",
        )
    if total and image_id >= total:
        raise HTTPException(
            status_code=400,
            detail=f"image_id {image_id} fora do intervalo (sessão tem {total} frames, índices 0–{total - 1}).",
        )
    obb = body.obb
    if session.mode == "obb":
        obb = body.obb or _obb_from_bbox(body.bbox)
        if obb.points is None:
            obb.points = _points_from_obb(obb)

    ann = Annotation(
        id=_state.next_ann_id[0],
        image_id=image_id,
        category_id=body.category_id,
        bbox=body.bbox,
        obb=obb,
        track_id=body.track_id,
        source=body.source,
    )
    _state.annotation_store.setdefault(image_id, []).append(ann)
    _state.next_ann_id[0] += 1
    _autosave(image_id)
    return ann


@router.post("/{image_id}/classification", response_model=ClassificationResult)
def classify_frame(image_id: int, body: ClassificationUpsert) -> ClassificationResult:
    session = _state.active_session()
    if session is None:
        raise HTTPException(status_code=404, detail="Sessao ativa nao encontrada.")
    if session.mode != "classification":
        raise HTTPException(status_code=422, detail="Endpoint disponivel apenas no modo classificacao.")
    if body.category_id >= len(session.classes):
        raise HTTPException(status_code=422, detail="category_id fora do intervalo de classes.")
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded. Call /frames/init first.")
    if image_id < 0 or image_id >= len(_state.frame_paths):
        raise HTTPException(status_code=400, detail="Index out of range.")

    from app.classification.dataset import (
        STATE_FILE_NAME,
        add_class_directory,
        load_state,
        prepare_dataset,
        transfer_image_to_class,
        write_state,
    )

    class_name = session.classes[body.category_id]
    state_path = session.output_path / STATE_FILE_NAME
    records = []
    class_directories = prepare_dataset(session.output_path, session.classes)
    if state_path.exists():
        try:
            state = load_state(state_path)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if state is not None:
            records = list(state.records)
            class_directories.update(state.class_directories)
    if class_name not in class_directories:
        add_class_directory(session.output_path, class_name, class_directories)

    image_path = _state.frame_paths[image_id]
    record = transfer_image_to_class(
        image_path,
        class_name=class_name,
        output_dir=session.output_path,
        class_directories=class_directories,
        move=body.move_file,
    )
    records.append(record)
    write_state(
        state_path,
        classes=session.classes,
        class_directories=class_directories,
        source_root=session.data_path,
        records=records,
    )
    session.saved_frames += 1
    session.annotation_count = len(records)

    return ClassificationResult(
        image_id=image_id,
        filename=image_path.name,
        top1_class_id=body.category_id,
        top1_class_name=class_name,
        destination_path=str(record.destination_path),
        operation=record.operation,
    )


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
