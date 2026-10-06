"""Pure data augmentation transforms for BGR images and YOLO labels."""

from __future__ import annotations

from typing import Any, List, Tuple

import numpy as np

from app.annotation.core.augmentation import geometric_transforms as geo
from app.annotation.core.augmentation import photometric_transforms as photo
from app.annotation.core.augmentation.augmentation_types import AugEntry, AugmentationPreset

YoloBox = List[Any]

# Chave do catálogo (augmentation_types) → transformação.
TRANSFORMS = {
    "flip_h": geo.flip_h,
    "flip_v": geo.flip_v,
    "rotate": geo.rotate,
    "shear": geo.shear,
    "crop": geo.crop,
    "brightness": photo.brightness,
    "contrast": photo.contrast,
    "saturation": photo.saturation,
    "hue": photo.hue,
    "grayscale": photo.grayscale,
    "blur": photo.blur,
    "noise": photo.noise,
    "cutout": photo.cutout,
}


def apply_preset(
    image: np.ndarray,
    bboxes_yolo: List[List],
    preset: AugmentationPreset,
) -> List[Tuple[np.ndarray, List[List]]]:
    """Applies enabled operations and returns augmented copies in memory."""
    if image is None or image.size == 0 or preset is None or not preset.enabled:
        return []

    copies = int(np.clip(preset.copies_per_image, 1, 5))
    enabled_entries = [entry for entry in preset.entries if entry.enabled]
    if not enabled_entries:
        return []

    rng = np.random.default_rng()
    results: List[Tuple[np.ndarray, List[List]]] = []
    for _ in range(copies):
        aug_image = image.copy()
        aug_boxes = [list(box) for box in bboxes_yolo]
        for entry in enabled_entries:
            aug_image, aug_boxes = _apply_entry(aug_image, aug_boxes, entry, rng)
            aug_boxes = _filter_valid_boxes(aug_boxes)
        results.append((aug_image, aug_boxes))
    return results


def _apply_entry(
    image: np.ndarray,
    boxes: List[YoloBox],
    entry: AugEntry,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, List[YoloBox]]:
    transform = TRANSFORMS.get(entry.key)
    if transform is None:
        return image, boxes
    return transform(image, boxes, entry.params or {}, rng)


def _filter_valid_boxes(boxes: List[YoloBox]) -> List[YoloBox]:
    valid: List[YoloBox] = []
    for box in boxes:
        if len(box) != 5:
            continue
        try:
            cx, cy, width, height = (float(value) for value in box[1:5])
        except (TypeError, ValueError):
            continue
        if width <= 0.0 or height <= 0.0:
            continue
        valid.append([
            box[0],
            float(np.clip(cx, 0.0, 1.0)),
            float(np.clip(cy, 0.0, 1.0)),
            float(np.clip(width, 0.0, 1.0)),
            float(np.clip(height, 0.0, 1.0)),
        ])
    return valid
