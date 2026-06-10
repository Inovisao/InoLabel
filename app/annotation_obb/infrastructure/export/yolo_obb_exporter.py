from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from app.annotation.core.export.split_service import assign_splits, normalize_split_ratios
from app.annotation.core.export.yolo_label_service import build_zero_based_category_mapping
from app.annotation_obb.geometry.obb_geometry import obb_to_points


def _image_lookup(payload: dict) -> Dict[int, dict]:
    return {int(image.get("id")): image for image in payload.get("images", []) if image.get("id") is not None}


def _format_obb_line(class_index: int, obb: dict, img_w: int, img_h: int) -> str:
    points = obb_to_points(
        float(obb["cx"]),
        float(obb["cy"]),
        float(obb["width"]),
        float(obb["height"]),
        float(obb.get("angle", 0.0)),
    )
    values = [str(class_index)]
    for x, y in points:
        values.append(f"{max(0.0, min(1.0, float(x) / max(img_w, 1))):.6f}")
        values.append(f"{max(0.0, min(1.0, float(y) / max(img_h, 1))):.6f}")
    return " ".join(values)


def _format_data_yaml(dataset_root: Path, names: Dict[int, str], splits: Optional[List[str]] = None) -> str:
    active = splits or ["train"]
    lines = [f"path: {dataset_root}"]
    for split in active:
        lines.append(f"{split}: images/{split}")
    lines.extend(["", "names:"])
    for class_id, name in names.items():
        lines.append(f"  {class_id}: {name}")
    return "\n".join(lines) + "\n"


def export_yolo_obb_dataset(
    payload: dict,
    output_dir: Path,
    source_images_dir: Optional[Path],
    split_ratios: Optional[Tuple[float, float, float]] = None,
    source_image_map: Optional[Dict[str, Path]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> dict:
    output_dir = Path(output_dir)

    class_mapping, names = build_zero_based_category_mapping(payload.get("categories", []))
    images_lookup = _image_lookup(payload)
    labels_by_image: Dict[int, List[str]] = {}

    for ann in payload.get("annotations", []):
        obb = ann.get("obb")
        if not isinstance(obb, dict):
            continue
        image = images_lookup.get(int(ann.get("image_id", -1)))
        if image is None:
            continue
        category_id = int(ann.get("category_id", -1))
        if category_id not in class_mapping:
            continue
        line = _format_obb_line(
            class_mapping[category_id],
            obb,
            int(image.get("width", 1)),
            int(image.get("height", 1)),
        )
        labels_by_image.setdefault(int(image["id"]), []).append(line)

    # Determine split assignments
    all_images = list(payload.get("images", []))
    if split_ratios is not None:
        normalized = normalize_split_ratios(split_ratios)
        split_assignments = assign_splits(all_images, normalized)
    else:
        split_assignments = {int(img.get("id")): "train" for img in all_images}

    # Create only the directories that will actually receive images
    splits_with_images = sorted(
        set(split_assignments.values()),
        key=lambda s: ("train", "val", "test").index(s) if s in ("train", "val", "test") else 99,
    )
    for split in splits_with_images:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    copied = 0
    images_per_split: Dict[str, int] = {s: 0 for s in splits_with_images}
    total_images = len(images_lookup)

    for image_id, image in images_lookup.items():
        file_name = str(image.get("file_name", ""))
        if not file_name:
            continue
        if source_image_map is not None:
            src = source_image_map.get(file_name)
            if src is None:
                continue
        elif source_images_dir is not None:
            src = source_images_dir / file_name
        else:
            continue
        if not src.exists():
            continue

        split = split_assignments.get(image_id, "train")
        dst = output_dir / "images" / split / file_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        label_path = output_dir / "labels" / split / Path(file_name).with_suffix(".txt")
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_lines = labels_by_image.get(image_id, [])
        label_path.write_text(
            "\n".join(label_lines) + ("\n" if label_lines else ""),
            encoding="utf-8",
        )
        copied += 1
        images_per_split[split] = images_per_split.get(split, 0) + 1
        if on_progress:
            on_progress(copied, total_images)

    (output_dir / "data.yaml").write_text(
        _format_data_yaml(output_dir, names, splits=splits_with_images),
        encoding="utf-8",
    )
    (output_dir / "annotations_obb.source.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "images": copied,
        "labels": sum(len(v) for v in labels_by_image.values()),
        "names": names,
        "images_per_split": images_per_split,
    }
