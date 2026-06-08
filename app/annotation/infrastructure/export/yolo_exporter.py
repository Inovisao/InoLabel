"""YOLO exporters and file writing utilities."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import cv2

from app.annotation.core.augmentation.augmentation_service import apply_preset
from app.annotation.core.augmentation.augmentation_types import AugmentationPreset
from app.annotation.core.export.split_service import assign_splits, normalize_split_ratios
from app.annotation.core.export.yolo_label_service import (
    annotations_to_yolo_bboxes,
    build_zero_based_category_mapping,
    format_yaml,
    format_yaml_no_split,
    format_yolo_boxes,
)


def _write_yolo_box_file(label_path: Path, boxes):
    label_path.write_text(format_yolo_boxes(boxes), encoding="utf-8")


def _write_augmented_copies(
    source_image_path: Path,
    target_image_path: Path,
    target_label_path: Path,
    yolo_boxes: List[List[Any]],
    augmentation_preset: Optional[AugmentationPreset],
    malformed_labels: List[str],
    present_classes: Set[int],
) -> Tuple[int, int]:
    if augmentation_preset is None or not augmentation_preset.enabled:
        return 0, 0

    image = cv2.imread(str(source_image_path))
    if image is None:
        malformed_labels.append(f"{target_image_path.name}: failed to read image for augmentation")
        return 0, 0

    written_images = 0
    written_labels = 0
    for idx, (aug_image, aug_boxes) in enumerate(apply_preset(image, yolo_boxes, augmentation_preset)):
        aug_image_path = target_image_path.with_name(
            f"{target_image_path.stem}_aug{idx + 1}{target_image_path.suffix}"
        )
        aug_label_path = target_label_path.with_name(f"{target_label_path.stem}_aug{idx + 1}.txt")
        if not cv2.imwrite(str(aug_image_path), aug_image):
            malformed_labels.append(f"{aug_image_path.name}: failed to save augmented image")
            continue
        _write_yolo_box_file(aug_label_path, aug_boxes)
        for box in aug_boxes:
            if len(box) == 5:
                present_classes.add(int(box[0]))
        written_images += 1
        written_labels += len(aug_boxes)
    return written_images, written_labels


def _normalized_split_ratios(split_ratios: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return normalize_split_ratios(split_ratios)



def _prepare_annotations(payload: Dict[str, Any]):
    annotations_by_image: Dict[int, List[Dict[str, Any]]] = {}
    for ann in payload.get("annotations", []):
        image_id = int(ann.get("image_id"))
        annotations_by_image.setdefault(image_id, []).append(ann)
    return annotations_by_image


def export_yolo_dataset(
    payload: Dict[str, Any],
    source_images_dir: Path,
    dataset_root: Path,
    split_ratios: Tuple[float, float, float] = (0.8, 0.1, 0.1),
    augmentation_preset: Optional[AugmentationPreset] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    normalized_ratios = _normalized_split_ratios(split_ratios)
    if dataset_root.exists():
        print(f"[AVISO] Removendo dataset existente antes de re-exportar: {dataset_root}")
        shutil.rmtree(dataset_root)

    images = payload.get("images", [])
    class_mapping, names = build_zero_based_category_mapping(payload.get("categories", []))
    if not names:
        raise ValueError("No valid categories found for YOLO export.")

    annotations_by_image = _prepare_annotations(payload)
    split_assignments = assign_splits(images, normalized_ratios)

    for split in ("train", "val", "test"):
        (dataset_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    images_per_split = {"train": 0, "val": 0, "test": 0}
    labels_per_split = {"train": 0, "val": 0, "test": 0}
    empty_images_per_split = {"train": 0, "val": 0, "test": 0}
    images_without_annotation: List[str] = []
    malformed_labels: List[str] = []
    present_classes: Set[int] = set()

    total_images = len(images)
    done = 0
    seen_names: Set[str] = set()

    for image in sorted(images, key=lambda item: str(item.get("file_name", ""))):
        image_id = int(image.get("id"))
        file_name = str(image.get("file_name", "")).strip()
        if not file_name:
            malformed_labels.append(f"image_id {image_id}: file_name is empty")
            continue
        if file_name in seen_names:
            raise ValueError(f"Duplicate image name found: {file_name}")
        seen_names.add(file_name)

        split = split_assignments.get(image_id, "train")
        source_image_path = source_images_dir / file_name
        if not source_image_path.exists():
            raise FileNotFoundError(f"Image not found for export: {source_image_path}")

        target_image_path = dataset_root / "images" / split / file_name
        target_label_path = dataset_root / "labels" / split / Path(file_name).with_suffix(".txt")
        target_image_path.parent.mkdir(parents=True, exist_ok=True)
        target_label_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_image_path, target_image_path)

        image_annotations = annotations_by_image.get(image_id, [])
        if not image_annotations:
            images_without_annotation.append(file_name)
            empty_images_per_split[split] += 1
        yolo_boxes = annotations_to_yolo_bboxes(
            image_annotations,
            class_mapping,
            int(image.get("width", 0)),
            int(image.get("height", 0)),
            malformed_labels,
            present_classes,
            target_label_path.name,
        )
        _write_yolo_box_file(target_label_path, yolo_boxes)
        images_per_split[split] += 1
        labels_per_split[split] += len(yolo_boxes)
        done += 1
        if on_progress:
            on_progress(done, total_images)

        if split == "train":
            aug_images, aug_labels = _write_augmented_copies(
                source_image_path,
                target_image_path,
                target_label_path,
                yolo_boxes,
                augmentation_preset,
                malformed_labels,
                present_classes,
            )
            images_per_split[split] += aug_images
            labels_per_split[split] += aug_labels

    data_yaml_path = dataset_root / "data.yaml"
    data_yaml_path.write_text(format_yaml(dataset_root, names), encoding="utf-8")
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


def export_yolo_no_split(
    payload: Dict[str, Any],
    source_images_dir: Path,
    dataset_root: Path,
    augmentation_preset: Optional[AugmentationPreset] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    if dataset_root.exists():
        print(f"[AVISO] Removendo dataset existente antes de re-exportar: {dataset_root}")
        shutil.rmtree(dataset_root)

    images = payload.get("images", [])
    class_mapping, names = build_zero_based_category_mapping(payload.get("categories", []))
    if not names:
        raise ValueError("No valid categories found for YOLO export.")
    annotations_by_image = _prepare_annotations(payload)

    (dataset_root / "images" / "all").mkdir(parents=True, exist_ok=True)
    (dataset_root / "labels" / "all").mkdir(parents=True, exist_ok=True)

    n_images = len(images)
    total_images = 0
    total_labels = 0
    done = 0
    images_without_annotation: List[str] = []
    malformed_labels: List[str] = []
    present_classes: Set[int] = set()

    seen_names: Set[str] = set()

    for image in sorted(images, key=lambda item: str(item.get("file_name", ""))):
        image_id = int(image.get("id"))
        file_name = str(image.get("file_name", "")).strip()
        if not file_name:
            malformed_labels.append(f"image_id {image_id}: file_name is empty")
            continue
        if file_name in seen_names:
            raise ValueError(f"Duplicate image name found: {file_name}")
        seen_names.add(file_name)

        source_image_path = source_images_dir / file_name
        if not source_image_path.exists():
            raise FileNotFoundError(f"Image not found for export: {source_image_path}")

        target_image_path = dataset_root / "images" / "all" / file_name
        target_label_path = dataset_root / "labels" / "all" / Path(file_name).with_suffix(".txt")
        target_image_path.parent.mkdir(parents=True, exist_ok=True)
        target_label_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_image_path, target_image_path)

        image_annotations = annotations_by_image.get(image_id, [])
        if not image_annotations:
            images_without_annotation.append(file_name)
        yolo_boxes = annotations_to_yolo_bboxes(
            image_annotations,
            class_mapping,
            int(image.get("width", 0)),
            int(image.get("height", 0)),
            malformed_labels,
            present_classes,
            target_label_path.name,
        )
        _write_yolo_box_file(target_label_path, yolo_boxes)
        total_images += 1
        total_labels += len(yolo_boxes)
        done += 1
        if on_progress:
            on_progress(done, n_images)

        aug_images, aug_labels = _write_augmented_copies(
            source_image_path,
            target_image_path,
            target_label_path,
            yolo_boxes,
            augmentation_preset,
            malformed_labels,
            present_classes,
        )
        total_images += aug_images
        total_labels += aug_labels

    data_yaml_path = dataset_root / "data.yaml"
    data_yaml_path.write_text(format_yaml_no_split(dataset_root, names), encoding="utf-8")
    return {
        "dataset_root": dataset_root.resolve(),
        "data_yaml": data_yaml_path.resolve(),
        "total_images": total_images,
        "total_labels": total_labels,
        "images_without_annotation": images_without_annotation,
        "malformed_labels": malformed_labels,
        "classes_present": {class_id: names[class_id] for class_id in sorted(present_classes)},
        "names": names,
    }
