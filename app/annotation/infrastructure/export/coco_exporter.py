"""COCO detection exporter."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

from app.annotation.core.export.yolo_label_service import clip_coco_bbox


def _flat_name(file_name: str) -> str:
    """Flattens a relative path to a single filename by replacing separators with '_'."""
    parts = Path(file_name).parts
    if len(parts) == 1:
        return parts[0]
    stem = "_".join(parts[:-1]) + "_" + Path(parts[-1]).stem
    return stem + Path(parts[-1]).suffix


def _unique_flat_names(file_names: Sequence[str]) -> Dict[str, str]:
    """Maps each relative file name to a distinct flat name for a single images/ folder."""
    mapping: Dict[str, str] = {}
    used: Set[str] = set()
    for file_name in file_names:
        if file_name in mapping:
            continue
        flat = _flat_name(file_name)
        stem, suffix = Path(flat).stem, Path(flat).suffix
        counter = 2
        while flat in used:
            flat = f"{stem}_{counter}{suffix}"
            counter += 1
        used.add(flat)
        mapping[file_name] = flat
    return mapping


def normalize_categories(categories: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": int(cat.get("id")),
            "name": str(cat.get("name", "")),
            "supercategory": str(cat.get("supercategory", "none")),
        }
        for cat in categories
    ]


def convert_tracking_to_detection(
    payload: Dict[str, Any], only_annotated_images: bool = False
) -> Dict[str, Any]:
    images = payload.get("images", [])
    annotations = payload.get("annotations", [])
    categories = payload.get("categories", [])

    image_sizes = {
        int(img.get("id")): (int(img.get("width", 0) or 0), int(img.get("height", 0) or 0))
        for img in images
    }

    image_ids_with_annotations: Set[int] = set()
    out_annotations: List[Dict[str, Any]] = []
    clipped_count = 0
    dropped_count = 0
    for ann in annotations:
        image_id = int(ann.get("image_id"))
        bbox = ann.get("bbox", [0, 0, 0, 0])
        area = float(ann.get("area", 0.0))
        width, height = image_sizes.get(image_id, (0, 0))
        if width > 0 and height > 0:
            # Nunca exportar caixa fora da resolucao declarada da imagem.
            clipped = clip_coco_bbox(bbox, width, height)
            if clipped is None:
                dropped_count += 1
                continue
            if list(clipped) != [float(v) for v in bbox]:
                clipped_count += 1
                area = clipped[2] * clipped[3]
            bbox = list(clipped)
        image_ids_with_annotations.add(image_id)
        out_annotations.append(
            {
                "id": int(ann.get("id")),
                "image_id": image_id,
                "category_id": int(ann.get("category_id")),
                "bbox": bbox,
                "area": area,
                "segmentation": ann.get("segmentation", []),
                "iscrowd": int(ann.get("iscrowd", 0)),
            }
        )

    if clipped_count or dropped_count:
        print(
            f"[AVISO] Export COCO: {clipped_count} bboxes recortadas aos limites da imagem, "
            f"{dropped_count} descartadas por ficarem sem area."
        )

    out_images: List[Dict[str, Any]] = []
    for img in images:
        image_id = int(img.get("id"))
        if only_annotated_images and image_id not in image_ids_with_annotations:
            continue
        out_images.append(
            {
                "id": image_id,
                "file_name": str(img.get("file_name", "")),
                "width": int(img.get("width", 0)),
                "height": int(img.get("height", 0)),
            }
        )

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_info = {
        "description": "COCO detection converted from tracking annotations",
        "version": "1.0",
        "date_created": now_iso,
    }
    if isinstance(payload.get("info"), dict):
        info = payload["info"]
        if "year" in info:
            out_info["year"] = info["year"]

    return {
        "info": out_info,
        "licenses": payload.get("licenses", []),
        "categories": normalize_categories(categories),
        "images": out_images,
        "annotations": out_annotations,
    }


def export_detection_coco_json(
    payload: Dict[str, Any],
    output_path: Path,
    only_annotated_images: bool = False,
    source_images_dir: Optional[Path] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """Writes a COCO detection JSON.

    With ``source_images_dir``, every image is copied into a single flat ``images/``
    folder next to the JSON (``sub/a.jpg`` -> ``sub_a.jpg``) and ``file_name`` is
    rewritten to match the copied file, so the exported JSON always resolves.
    """
    converted = convert_tracking_to_detection(payload, only_annotated_images=only_annotated_images)
    imgs = converted.get("images", [])

    copies: List[tuple] = []
    if source_images_dir is not None:
        flat_names = _unique_flat_names([str(img.get("file_name", "")).strip() for img in imgs])
        for img in imgs:
            file_name = str(img.get("file_name", "")).strip()
            if not file_name:
                continue
            src = source_images_dir / file_name
            if not src.exists():
                raise FileNotFoundError(f"Image not found for export: {src}")
            img["file_name"] = flat_names[file_name]
            copies.append((src, img["file_name"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2, ensure_ascii=False)

    if source_images_dir is not None:
        images_dest = output_path.parent / "images"
        images_dest.mkdir(parents=True, exist_ok=True)
        total = len(copies)
        for done, (src, flat_name) in enumerate(copies, 1):
            shutil.copy2(src, images_dest / flat_name)
            if on_progress:
                on_progress(done, total)

    return converted
