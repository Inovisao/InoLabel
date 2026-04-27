"""Utilitarios para exportacao de anotacoes em COCO e YOLO."""

from __future__ import annotations

import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_categories(categories: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for cat in categories:
        normalized.append(
            {
                "id": int(cat.get("id")),
                "name": str(cat.get("name", "")),
                "supercategory": str(cat.get("supercategory", "none")),
            }
        )
    return normalized


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
    payload: Dict[str, Any], output_path: Path, only_annotated_images: bool = False
) -> Dict[str, Any]:
    converted = convert_tracking_to_detection(payload, only_annotated_images=only_annotated_images)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2, ensure_ascii=False)
    return converted


def _build_zero_based_category_mapping(
    categories: Sequence[Dict[str, Any]],
) -> Tuple[Dict[int, int], Dict[int, str]]:
    old_to_new: Dict[int, int] = {}
    names: Dict[int, str] = {}
    for cat in categories:
        name = str(cat.get("name", "")).strip()
        if not name:
            continue
        old_id = int(cat.get("id"))
        if old_id in old_to_new:
            continue
        new_id = len(old_to_new)
        old_to_new[old_id] = new_id
        names[new_id] = name
    return old_to_new, names


def _compute_split_counts(total: int, split_ratios: Tuple[float, float, float]) -> Dict[str, int]:
    if total <= 0:
        return {"train": 0, "val": 0, "test": 0}
    if total < 3:
        return {"train": total, "val": 0, "test": 0}

    train_ratio, val_ratio, test_ratio = split_ratios
    raw_counts = {
        "train": total * train_ratio,
        "val": total * val_ratio,
        "test": total * test_ratio,
    }
    counts = {name: int(math.floor(value)) for name, value in raw_counts.items()}
    remainder = total - sum(counts.values())
    fractional = sorted(
        ((raw_counts[name] - counts[name], name) for name in ("train", "val", "test")),
        reverse=True,
    )
    for _, name in fractional[:remainder]:
        counts[name] += 1

    if counts["train"] == 0:
        donor = "val" if counts["val"] > counts["test"] else "test"
        if counts[donor] > 1:
            counts[donor] -= 1
            counts["train"] += 1
    return counts


def _assign_splits(images: Sequence[Dict[str, Any]], split_ratios: Tuple[float, float, float]) -> Dict[int, str]:
    ordered_images = sorted(images, key=lambda image: str(image.get("file_name", "")))
    counts = _compute_split_counts(len(ordered_images), split_ratios)
    assignments: Dict[int, str] = {}
    cursor = 0
    for split in ("train", "val", "test"):
        for image in ordered_images[cursor : cursor + counts[split]]:
            assignments[int(image.get("id"))] = split
        cursor += counts[split]
    return assignments


def _format_yaml(dataset_root: Path, names: Dict[int, str]) -> str:
    lines = [
        f"path: {dataset_root.resolve()}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        "",
        "names:",
    ]
    for class_id, name in names.items():
        lines.append(f"  {class_id}: {name}")
    return "\n".join(lines) + "\n"


def _normalize_yolo_bbox(
    bbox: Sequence[Any], image_width: int, image_height: int
) -> Optional[Tuple[float, float, float, float]]:
    if len(bbox) != 4 or image_width <= 0 or image_height <= 0:
        return None
    x, y, width, height = (float(value) for value in bbox)
    if width <= 0 or height <= 0:
        return None

    x_center = (x + (width / 2.0)) / float(image_width)
    y_center = (y + (height / 2.0)) / float(image_height)
    norm_width = width / float(image_width)
    norm_height = height / float(image_height)
    values = (x_center, y_center, norm_width, norm_height)

    if any(value < 0.0 or value > 1.0 for value in values):
        return None
    return values


def _write_label_file(
    label_path: Path,
    annotations: Iterable[Dict[str, Any]],
    class_mapping: Dict[int, int],
    image_width: int,
    image_height: int,
    malformed_labels: List[str],
    present_classes: Set[int],
) -> int:
    lines: List[str] = []
    label_count = 0
    for ann in annotations:
        original_class_id = int(ann.get("category_id", -1))
        if original_class_id not in class_mapping:
            malformed_labels.append(
                f"{label_path.name}: category_id invalido {original_class_id} na anotacao {ann.get('id')}"
            )
            continue
        normalized = _normalize_yolo_bbox(ann.get("bbox", []), image_width, image_height)
        if normalized is None:
            malformed_labels.append(
                f"{label_path.name}: bbox invalido na anotacao {ann.get('id')} -> {ann.get('bbox')}"
            )
            continue
        class_id = class_mapping[original_class_id]
        present_classes.add(class_id)
        x_center, y_center, norm_width, norm_height = normalized
        lines.append(
            f"{class_id} {x_center:.6f} {y_center:.6f} {norm_width:.6f} {norm_height:.6f}"
        )
        label_count += 1

    label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return label_count


def export_yolo_dataset(
    payload: Dict[str, Any],
    source_images_dir: Path,
    dataset_root: Path,
    split_ratios: Tuple[float, float, float] = (0.8, 0.1, 0.1),
) -> Dict[str, Any]:
    if len(split_ratios) != 3:
        raise ValueError("split_ratios deve conter train, val e test.")
    if any(ratio < 0 for ratio in split_ratios):
        raise ValueError("split_ratios nao pode conter valores negativos.")
    total_ratio = sum(split_ratios)
    if total_ratio <= 0:
        raise ValueError("split_ratios precisa ter soma positiva.")
    normalized_ratios = tuple(ratio / total_ratio for ratio in split_ratios)
    if dataset_root.exists():
        shutil.rmtree(dataset_root)

    images = payload.get("images", [])
    annotations = payload.get("annotations", [])
    categories = payload.get("categories", [])

    class_mapping, names = _build_zero_based_category_mapping(categories)
    if not names:
        raise ValueError("Nenhuma categoria valida encontrada para exportacao YOLO.")

    annotations_by_image: Dict[int, List[Dict[str, Any]]] = {}
    for ann in annotations:
        image_id = int(ann.get("image_id"))
        annotations_by_image.setdefault(image_id, []).append(ann)
    split_assignments = _assign_splits(images, normalized_ratios)

    for split in ("train", "val", "test"):
        (dataset_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    images_per_split = {"train": 0, "val": 0, "test": 0}
    labels_per_split = {"train": 0, "val": 0, "test": 0}
    empty_images_per_split = {"train": 0, "val": 0, "test": 0}
    images_without_annotation: List[str] = []
    malformed_labels: List[str] = []
    present_classes: Set[int] = set()

    seen_names: Set[str] = set()
    for image in sorted(images, key=lambda item: str(item.get("file_name", ""))):
        image_id = int(image.get("id"))
        file_name = str(image.get("file_name", "")).strip()
        if not file_name:
            malformed_labels.append(f"image_id {image_id}: file_name vazio")
            continue
        if file_name in seen_names:
            raise ValueError(f"Nome de imagem duplicado encontrado: {file_name}")
        seen_names.add(file_name)

        split = split_assignments.get(image_id, "train")
        source_image_path = source_images_dir / file_name
        if not source_image_path.exists():
            raise FileNotFoundError(f"Imagem nao encontrada para exportacao: {source_image_path}")

        target_image_path = dataset_root / "images" / split / file_name
        target_label_path = dataset_root / "labels" / split / Path(file_name).with_suffix(".txt")
        target_image_path.parent.mkdir(parents=True, exist_ok=True)
        target_label_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_image_path, target_image_path)

        image_width = int(image.get("width", 0))
        image_height = int(image.get("height", 0))
        image_annotations = annotations_by_image.get(image_id, [])
        if not image_annotations:
            images_without_annotation.append(file_name)
            empty_images_per_split[split] += 1
        label_count = _write_label_file(
            target_label_path,
            image_annotations,
            class_mapping,
            image_width,
            image_height,
            malformed_labels,
            present_classes,
        )
        images_per_split[split] += 1
        labels_per_split[split] += label_count

    data_yaml_path = dataset_root / "data.yaml"
    data_yaml_path.write_text(_format_yaml(dataset_root, names), encoding="utf-8")

    return {
        "dataset_root": dataset_root.resolve(),
        "data_yaml": data_yaml_path.resolve(),
        "images_per_split": images_per_split,
        "labels_per_split": labels_per_split,
        "empty_images_per_split": empty_images_per_split,
        "images_without_annotation": images_without_annotation,
        "malformed_labels": malformed_labels,
        "classes_present": {class_id: names[class_id] for class_id in sorted(present_classes)},
        "names": names,
    }
