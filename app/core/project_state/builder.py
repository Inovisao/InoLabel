"""Anotações em memória → COCO do projeto (o mesmo payload que a exportação usa)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app import __version__ as APP_VERSION
from app.annotation.core.export.yolo_label_service import clip_coco_bbox
from app.core.palette import CLASS_COLORS
from app.core.project_state.paths import relative_name


def _field(ann, name, default=None):
    """Lê um campo de um Annotation (pydantic) ou de um dict."""
    if isinstance(ann, Mapping):
        return ann.get(name, default)
    return getattr(ann, name, default)


def build_payload(
    *,
    mode: str,
    classes: Sequence[str],
    data_path: Optional[Path],
    frame_paths: Sequence[Path],
    frame_dims: Mapping[int, Tuple[int, int]],
    annotation_store: Mapping[int, Iterable],
    reviewed: Iterable[int] = (),
    image_ids: Optional[Dict[str, int]] = None,
    current_index: Optional[int] = None,
    keypoint_specs: Sequence[Mapping] = (),
) -> dict:
    """Monta o COCO do projeto a partir do estado em memória.

    ``image_ids`` (``file_name → id``) é atualizado no lugar: imagens novas recebem
    o próximo id livre, e as já conhecidas mantêm o seu.
    Frames sem dimensões conhecidas são omitidos — quem chama garante as dimensões.
    """
    image_ids = image_ids if image_ids is not None else {}
    reviewed = set(reviewed)
    indices = sorted(
        idx for idx in set(annotation_store) | reviewed
        if 0 <= idx < len(frame_paths) and (annotation_store.get(idx) or idx in reviewed)
    )

    images: List[dict] = []
    annotations: List[dict] = []
    next_image_id = max(image_ids.values(), default=0) + 1
    for idx in indices:
        dims = frame_dims.get(idx)
        if not dims or not dims[0] or not dims[1]:
            continue
        width, height = int(dims[0]), int(dims[1])
        name = relative_name(frame_paths[idx], data_path)
        if name not in image_ids:
            image_ids[name] = next_image_id
            next_image_id += 1
        image_id = image_ids[name]
        images.append({"id": image_id, "file_name": name, "width": width, "height": height})

        for ann in annotation_store.get(idx) or []:
            category = int(_field(ann, "category_id", -1))
            if category < 0 or category >= len(classes):
                continue
            if mode == "keypoint":
                entry = _keypoint_entry(ann, image_id, category, width, height)
            else:
                entry = _box_entry(ann, image_id, category, width, height, mode)
            if entry is not None:
                annotations.append(entry)

    payload = {
        "info": {
            "description": "InoLabel — estado do projeto",
            "version": "1.0",
            "app_version": APP_VERSION,
            "task_mode": mode,
            "data_root": str(data_path) if data_path is not None else "",
        },
        "licenses": [],
        "categories": [_category(i, name, mode, keypoint_specs) for i, name in enumerate(classes)],
        "images": images,
        "annotations": annotations,
    }
    if current_index is not None and 0 <= current_index < len(frame_paths):
        payload["annotation_state"] = {
            "last_active_file_name": relative_name(frame_paths[current_index], data_path),
            "last_active_frame_index": int(current_index),
        }
    return payload


def _category(index: int, name: str, mode: str, keypoint_specs: Sequence[Mapping]) -> dict:
    category = {"id": index + 1, "name": name, "color": CLASS_COLORS[index % len(CLASS_COLORS)], "supercategory": "none"}
    if mode == "keypoint":
        spec = keypoint_specs[index] if index < len(keypoint_specs) else {}
        category["keypoints"] = list(spec.get("keypoints", []))
        category["skeleton"] = [list(link) for link in spec.get("skeleton", [])]
    return category


def _keypoint_entry(ann, image_id: int, category: int, width: int, height: int) -> Optional[dict]:
    """Anotação no padrão COCO Keypoints; pontos presos à imagem, bbox = envelope dos visíveis."""
    points = _field(ann, "keypoints") or []
    flat: List[float] = []
    placed = []
    for kp in points:
        x, y, v = float(kp[0]), float(kp[1]), int(kp[2])
        if v > 0:
            x, y = min(max(x, 0.0), float(width)), min(max(y, 0.0), float(height))
            placed.append((x, y))
        else:
            x = y = 0.0
        flat.extend([x, y, v])
    if not placed:
        return None   # instância sem nenhum ponto marcado não é válida
    xs = [p[0] for p in placed]
    ys = [p[1] for p in placed]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    score = _field(ann, "score")
    return {
        "id": int(_field(ann, "id")),
        "image_id": image_id,
        "category_id": category + 1,
        "bbox": [x0, y0, w, h],
        "area": w * h,
        "iscrowd": 0,
        "segmentation": [],
        "keypoints": flat,
        "num_keypoints": len(placed),
        "score": float(score) if score is not None else 1.0,
        "source": _field(ann, "source", "manual") or "manual",
    }


def _box_entry(ann, image_id: int, category: int, width: int, height: int, mode: str) -> Optional[dict]:
    """Anotação de caixa (detecção, rastreamento, OBB); bbox recortada à imagem."""
    clipped = clip_coco_bbox(list(_field(ann, "bbox", [])), width, height)
    if clipped is None:
        return None
    x, y, w, h = clipped
    score = _field(ann, "score")
    entry = {
        "id": int(_field(ann, "id")),
        "image_id": image_id,
        "category_id": category + 1,
        "bbox": [x, y, w, h],
        "area": w * h,
        "iscrowd": 0,
        "segmentation": [],
        "score": float(score) if score is not None else 1.0,
        "source": _field(ann, "source", "manual") or "manual",
    }
    track_id = _field(ann, "track_id")
    if mode == "tracking" and track_id is not None:
        entry["track_id"] = int(track_id)
    obb = _field(ann, "obb")
    if obb is not None:
        entry["obb"] = obb if isinstance(obb, Mapping) else obb.model_dump(exclude_none=True)
    return entry
