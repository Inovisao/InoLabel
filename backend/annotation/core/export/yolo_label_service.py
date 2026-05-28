"""Logica pura de labels YOLO e conversao de bboxes."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


def build_zero_based_category_mapping(
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


def normalize_yolo_bbox(
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


def annotations_to_yolo_bboxes(
    annotations: Iterable[Dict[str, Any]],
    class_mapping: Dict[int, int],
    image_width: int,
    image_height: int,
    malformed_labels: List[str],
    present_classes: Set[int],
    label_name: str,
) -> List[List[Any]]:
    boxes: List[List[Any]] = []
    for ann in annotations:
        original_class_id = int(ann.get("category_id", -1))
        if original_class_id not in class_mapping:
            malformed_labels.append(
                f"{label_name}: category_id invalido {original_class_id} na anotacao {ann.get('id')}"
            )
            continue
        normalized = normalize_yolo_bbox(ann.get("bbox", []), image_width, image_height)
        if normalized is None:
            malformed_labels.append(
                f"{label_name}: bbox invalido na anotacao {ann.get('id')} -> {ann.get('bbox')}"
            )
            continue
        class_id = class_mapping[original_class_id]
        present_classes.add(class_id)
        x_center, y_center, norm_width, norm_height = normalized
        boxes.append([class_id, x_center, y_center, norm_width, norm_height])
    return boxes


def format_yolo_boxes(boxes: Sequence[Sequence[Any]]) -> str:
    lines: List[str] = []
    for box in boxes:
        if len(box) != 5:
            continue
        class_id, x_center, y_center, norm_width, norm_height = box
        lines.append(
            f"{int(class_id)} {float(x_center):.6f} {float(y_center):.6f} "
            f"{float(norm_width):.6f} {float(norm_height):.6f}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def format_yaml(dataset_root, names: Dict[int, str]) -> str:
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


def format_yaml_no_split(dataset_root, names: Dict[int, str]) -> str:
    lines = [
        f"path: {dataset_root.resolve()}",
        "train: images/all",
        "val: images/all",
        "test: images/all",
        "",
        "names:",
    ]
    for class_id, name in names.items():
        lines.append(f"  {class_id}: {name}")
    return "\n".join(lines) + "\n"
