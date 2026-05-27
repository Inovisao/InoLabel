"""Exportador COCO de deteccao."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set


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

    image_ids_with_annotations: Set[int] = set()
    out_annotations: List[Dict[str, Any]] = []
    for ann in annotations:
        image_id = int(ann.get("image_id"))
        image_ids_with_annotations.add(image_id)
        out_annotations.append(
            {
                "id": int(ann.get("id")),
                "image_id": image_id,
                "category_id": int(ann.get("category_id")),
                "bbox": ann.get("bbox", [0, 0, 0, 0]),
                "area": float(ann.get("area", 0.0)),
                "segmentation": ann.get("segmentation", []),
                "iscrowd": int(ann.get("iscrowd", 0)),
            }
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
) -> Dict[str, Any]:
    converted = convert_tracking_to_detection(payload, only_annotated_images=only_annotated_images)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2, ensure_ascii=False)

    if source_images_dir is not None:
        images_dest = output_path.parent / "images"
        images_dest.mkdir(parents=True, exist_ok=True)
        for img in converted.get("images", []):
            file_name = str(img.get("file_name", "")).strip()
            if not file_name:
                continue
            src = source_images_dir / file_name
            if not src.exists():
                continue
            dst = images_dest / Path(file_name).name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    return converted
