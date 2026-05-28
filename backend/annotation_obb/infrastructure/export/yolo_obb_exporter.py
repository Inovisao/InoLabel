from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from backend.annotation.core.export.yolo_label_service import build_zero_based_category_mapping
from backend.annotation_obb.geometry.obb_geometry import obb_to_points


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


def _format_data_yaml(dataset_root: Path, names: Dict[int, str]) -> str:
    lines = [
        f"path: {dataset_root}",
        "train: images/train",
        "val: images/val",
        "",
        "names:",
    ]
    for class_id, name in names.items():
        lines.append(f"  {class_id}: {name}")
    return "\n".join(lines) + "\n"


def export_yolo_obb_dataset(payload: dict, output_dir: Path, source_images_dir: Path) -> dict:
    output_dir = Path(output_dir)
    images_dir = output_dir / "images" / "train"
    labels_dir = output_dir / "labels" / "train"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    class_mapping, names = build_zero_based_category_mapping(payload.get("categories", []))
    images = _image_lookup(payload)
    labels_by_image: Dict[int, List[str]] = {}

    for ann in payload.get("annotations", []):
        obb = ann.get("obb")
        if not isinstance(obb, dict):
            continue
        image = images.get(int(ann.get("image_id", -1)))
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

    copied = 0
    for image_id, image in images.items():
        file_name = str(image.get("file_name", ""))
        if not file_name:
            continue
        src = source_images_dir / file_name
        if not src.exists():
            continue
        dst = images_dir / file_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        label_path = labels_dir / Path(file_name).with_suffix(".txt")
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.write_text("\n".join(labels_by_image.get(image_id, [])) + "\n", encoding="utf-8")
        copied += 1

    (output_dir / "data.yaml").write_text(_format_data_yaml(output_dir, names), encoding="utf-8")
    (output_dir / "annotations_obb.source.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"images": copied, "labels": sum(len(v) for v in labels_by_image.values()), "names": names}
