"""YOLO exporters and file writing utilities."""

from __future__ import annotations

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _safe_resolve_within(root: Path, *parts: str) -> Path:
    """Join parts to root, resolve and ensure the resulting path is within root.

    Raises ValueError if resolution escapes the root (prevents path traversal).
    """
    dest = (root.joinpath(*parts)).resolve()
    root_resolved = root.resolve()
    try:
        # On Windows compare case-insensitively by normalizing case
        if str(dest).startswith(str(root_resolved)):
            return dest
        raise ValueError(f"Resolved path escapes allowed root: {dest}")
    except Exception:
        raise


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


def _resolve_source(
    file_name: str,
    source_images_dir: Optional[Path],
    source_image_map: Optional[Dict[str, Path]],
) -> Path:
    """Return the source path for file_name using map when available, directory otherwise."""
    if source_image_map is not None:
        src = source_image_map.get(file_name)
        if src is None or not src.exists():
            raise FileNotFoundError(f"Image not found for export: {file_name}")
        return src
    if source_images_dir is None:
        raise ValueError("Either source_images_dir or source_image_map must be provided.")
    src = _safe_resolve_within(source_images_dir, file_name)
    if not src.exists():
        raise FileNotFoundError(f"Image not found for export: {src}")
    return src


def export_yolo_dataset(
    payload: Dict[str, Any],
    source_images_dir: Optional[Path],
    dataset_root: Path,
    split_ratios: Tuple[float, float, float] = (0.8, 0.1, 0.1),
    augmentation_preset: Optional[AugmentationPreset] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    source_image_map: Optional[Dict[str, Path]] = None,
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
    seen_names: Set[str] = set()

    # --- Sequential validation phase: resolve paths, detect duplicates ---
    work_items: List[Tuple] = []
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
        source_path = _resolve_source(file_name, source_images_dir, source_image_map)

        target_images_root = dataset_root / "images" / split
        target_labels_root = dataset_root / "labels" / split
        target_image_path = _safe_resolve_within(target_images_root, file_name)
        target_label_path = _safe_resolve_within(
            target_labels_root, Path(file_name).with_suffix(".txt").as_posix()
        )
        image_annotations = annotations_by_image.get(image_id, [])
        work_items.append((
            file_name, split, source_path,
            target_image_path, target_label_path,
            image_annotations,
            int(image.get("width", 0)), int(image.get("height", 0)),
            not image_annotations,
        ))

    # --- Parallel processing phase: copy + label write per image ---
    _lock = threading.Lock()
    _done = [0]

    def _process_one(item: Tuple) -> Tuple:
        (fname, split, src_path, tgt_img, tgt_lbl,
         ann_list, img_w, img_h, is_empty) = item
        local_malformed: List[str] = []
        local_present: Set[int] = set()

        tgt_img.parent.mkdir(parents=True, exist_ok=True)
        tgt_lbl.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, tgt_img)

        yolo_boxes = annotations_to_yolo_bboxes(
            ann_list, class_mapping, img_w, img_h,
            local_malformed, local_present, tgt_lbl.name,
        )

        try:
            tmp_lbl = tgt_lbl.with_name(tgt_lbl.name + ".tmp")
            tmp_lbl.write_text(format_yolo_boxes(yolo_boxes), encoding="utf-8")
            tmp_lbl.replace(tgt_lbl)
        except Exception:
            try:
                tmp_lbl.unlink(missing_ok=True)
            except Exception:
                pass
            raise

        aug_imgs = aug_labels = 0
        if split == "train":
            aug_imgs, aug_labels = _write_augmented_copies(
                src_path, tgt_img, tgt_lbl, yolo_boxes,
                augmentation_preset, local_malformed, local_present,
            )

        return fname, split, is_empty, local_malformed, local_present, 1 + aug_imgs, len(yolo_boxes) + aug_labels

    n_workers = min(4, os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=n_workers) as exe:
        futures = [exe.submit(_process_one, item) for item in work_items]
        for f in as_completed(futures):
            fname, split, is_empty, loc_mal, loc_pres, n_imgs, n_lbls = f.result()
            malformed_labels.extend(loc_mal)
            present_classes.update(loc_pres)
            images_per_split[split] += n_imgs
            labels_per_split[split] += n_lbls
            if is_empty:
                images_without_annotation.append(fname)
                empty_images_per_split[split] += 1
            with _lock:
                _done[0] += 1
                if on_progress:
                    on_progress(_done[0], total_images)

    # Write data.yaml atomically
    data_yaml_path = dataset_root / "data.yaml"
    tmp_data_yaml = data_yaml_path.with_name(data_yaml_path.name + ".tmp")
    tmp_data_yaml.write_text(format_yaml(dataset_root, names), encoding="utf-8")
    tmp_data_yaml.replace(data_yaml_path)
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
    source_images_dir: Optional[Path],
    dataset_root: Path,
    augmentation_preset: Optional[AugmentationPreset] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    source_image_map: Optional[Dict[str, Path]] = None,
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
    images_without_annotation: List[str] = []
    malformed_labels: List[str] = []
    present_classes: Set[int] = set()
    seen_names: Set[str] = set()

    # --- Sequential validation phase ---
    work_items: List[Tuple] = []
    for image in sorted(images, key=lambda item: str(item.get("file_name", ""))):
        image_id = int(image.get("id"))
        file_name = str(image.get("file_name", "")).strip()
        if not file_name:
            malformed_labels.append(f"image_id {image_id}: file_name is empty")
            continue
        if file_name in seen_names:
            raise ValueError(f"Duplicate image name found: {file_name}")
        seen_names.add(file_name)

        source_path = _resolve_source(file_name, source_images_dir, source_image_map)

        target_images_root = dataset_root / "images" / "all"
        target_labels_root = dataset_root / "labels" / "all"
        target_image_path = _safe_resolve_within(target_images_root, file_name)
        target_label_path = _safe_resolve_within(
            target_labels_root, Path(file_name).with_suffix(".txt").as_posix()
        )
        image_annotations = annotations_by_image.get(image_id, [])
        work_items.append((
            file_name, source_path,
            target_image_path, target_label_path,
            image_annotations,
            int(image.get("width", 0)), int(image.get("height", 0)),
            not image_annotations,
        ))

    # --- Parallel processing phase ---
    _lock = threading.Lock()
    _done = [0]

    def _process_one(item: Tuple) -> Tuple:
        (fname, src_path, tgt_img, tgt_lbl,
         ann_list, img_w, img_h, is_empty) = item
        local_malformed: List[str] = []
        local_present: Set[int] = set()

        tgt_img.parent.mkdir(parents=True, exist_ok=True)
        tgt_lbl.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, tgt_img)

        yolo_boxes = annotations_to_yolo_bboxes(
            ann_list, class_mapping, img_w, img_h,
            local_malformed, local_present, tgt_lbl.name,
        )

        try:
            tmp_lbl = tgt_lbl.with_name(tgt_lbl.name + ".tmp")
            tmp_lbl.write_text(format_yolo_boxes(yolo_boxes), encoding="utf-8")
            tmp_lbl.replace(tgt_lbl)
        except Exception:
            try:
                tmp_lbl.unlink(missing_ok=True)
            except Exception:
                pass
            raise

        aug_imgs, aug_labels = _write_augmented_copies(
            src_path, tgt_img, tgt_lbl, yolo_boxes,
            augmentation_preset, local_malformed, local_present,
        )

        return fname, is_empty, local_malformed, local_present, 1 + aug_imgs, len(yolo_boxes) + aug_labels

    n_workers = min(4, os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=n_workers) as exe:
        futures = [exe.submit(_process_one, item) for item in work_items]
        for f in as_completed(futures):
            fname, is_empty, loc_mal, loc_pres, n_imgs, n_lbls = f.result()
            malformed_labels.extend(loc_mal)
            present_classes.update(loc_pres)
            total_images += n_imgs
            total_labels += n_lbls
            if is_empty:
                images_without_annotation.append(fname)
            with _lock:
                _done[0] += 1
                if on_progress:
                    on_progress(_done[0], n_images)

    # Write data.yaml atomically
    data_yaml_path = dataset_root / "data.yaml"
    tmp_data_yaml = data_yaml_path.with_name(data_yaml_path.name + ".tmp")
    tmp_data_yaml.write_text(format_yaml_no_split(dataset_root, names), encoding="utf-8")
    tmp_data_yaml.replace(data_yaml_path)
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
