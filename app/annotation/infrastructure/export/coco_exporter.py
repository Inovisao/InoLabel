"""COCO detection exporter."""

from __future__ import annotations

import json
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple


def _flat_name(file_name: str) -> str:
    """Flattens a relative path to a single filename by replacing separators with '_'."""
    parts = Path(file_name).parts
    if len(parts) == 1:
        return parts[0]
    stem = "_".join(parts[:-1]) + "_" + Path(parts[-1]).stem
    return stem + Path(parts[-1]).suffix


def _flat_name_unique(file_name: str, used_names: Set[str]) -> str:
    """Return a collision-free flat name by appending a numeric suffix when needed."""
    candidate = _flat_name(file_name)
    if candidate not in used_names:
        return candidate
    base = Path(candidate).stem
    suffix = Path(candidate).suffix
    counter = 1
    while True:
        new_name = f"{base}_{counter}{suffix}"
        if new_name not in used_names:
            return new_name
        counter += 1


def normalize_categories(categories: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": int(cat.get("id")),
            "name": str(cat.get("name", "")),
            "supercategory": str(cat.get("supercategory", "none")),
        }
        for cat in categories
    ]


_OPTIONAL_ANNOTATION_FIELDS = ("score", "source", "track_id", "video", "obb")


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
        entry: Dict[str, Any] = {
            "id": int(ann.get("id")),
            "image_id": image_id,
            "category_id": int(ann.get("category_id")),
            "bbox": ann.get("bbox", [0, 0, 0, 0]),
            "area": float(ann.get("area", 0.0)),
            "segmentation": ann.get("segmentation", []),
            "iscrowd": int(ann.get("iscrowd", 0)),
        }
        for field in _OPTIONAL_ANNOTATION_FIELDS:
            if field in ann:
                entry[field] = ann[field]
        out_annotations.append(entry)

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
    source_image_map: Optional[Dict[str, Path]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    converted = convert_tracking_to_detection(payload, only_annotated_images=only_annotated_images)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = output_path.with_name(output_path.name + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(converted, f, indent=2, ensure_ascii=False)
        tmp_path.replace(output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    if source_images_dir is not None or source_image_map is not None:
        imgs = converted.get("images", [])
        images_dest = output_path.parent / "images"
        images_dest.mkdir(parents=True, exist_ok=True)

        # Sequential phase: resolve names and deduplicate (must be serial for collision tracking)
        used_flat_names: Set[str] = set()
        copy_jobs: List[Tuple[Path, Path]] = []
        for img in imgs:
            file_name = str(img.get("file_name", "")).strip()
            if not file_name:
                continue
            if source_image_map is not None:
                src = source_image_map.get(file_name)
                if src is None or not src.exists():
                    continue
            else:
                src = source_images_dir / file_name  # type: ignore[operator]
                if not src.exists():
                    continue
            flat = _flat_name_unique(file_name, used_flat_names)
            used_flat_names.add(flat)
            copy_jobs.append((src, images_dest / flat))

        # Parallel phase: copy images concurrently
        total = len(copy_jobs)
        done_count = [0]
        lock = threading.Lock()

        def _copy_one(job: Tuple[Path, Path]) -> None:
            src, dst = job
            shutil.copy2(src, dst)
            with lock:
                done_count[0] += 1
                if on_progress:
                    on_progress(done_count[0], total)

        n_workers = min(4, os.cpu_count() or 4)
        with ThreadPoolExecutor(max_workers=n_workers) as exe:
            futures = [exe.submit(_copy_one, job) for job in copy_jobs]
            for f in as_completed(futures):
                f.result()

    return converted
