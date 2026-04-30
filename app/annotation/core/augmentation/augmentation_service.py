"""Transformacoes puras de data augmentation para imagens BGR e labels YOLO."""

from __future__ import annotations

import math
from typing import Any, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from app.annotation.core.augmentation.augmentation_types import AugEntry, AugmentationPreset

YoloBox = List[Any]


def apply_preset(
    image: np.ndarray,
    bboxes_yolo: List[List],
    preset: AugmentationPreset,
) -> List[Tuple[np.ndarray, List[List]]]:
    """Aplica operacoes habilitadas e retorna copias aumentadas em memoria."""
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
    key = entry.key
    params = entry.params or {}

    if key == "flip_h":
        if not _passes_prob(params, rng):
            return image, boxes
        flipped = cv2.flip(image, 1)
        return flipped, [[box[0], 1.0 - float(box[1]), box[2], box[3], box[4]] for box in boxes]

    if key == "flip_v":
        if not _passes_prob(params, rng):
            return image, boxes
        flipped = cv2.flip(image, 0)
        return flipped, [[box[0], box[1], 1.0 - float(box[2]), box[3], box[4]] for box in boxes]

    if key == "rotate":
        if not _passes_prob(params, rng):
            return image, boxes
        max_degrees = _float_param(params, "max_degrees", 15.0)
        angle = float(rng.uniform(-max_degrees, max_degrees))
        return _warp_with_matrix(image, boxes, _rotation_matrix(image, angle))

    if key == "shear":
        if not _passes_prob(params, rng):
            return image, boxes
        max_degrees = _float_param(params, "max_degrees", 10.0)
        angle = float(rng.uniform(-max_degrees, max_degrees))
        shear = math.tan(math.radians(angle))
        height, width = image.shape[:2]
        matrix = np.array([[1.0, shear, -shear * width / 2.0], [0.0, 1.0, 0.0]], dtype=np.float32)
        return _warp_with_matrix(image, boxes, matrix)

    if key == "crop":
        if not _passes_prob(params, rng):
            return image, boxes
        return _random_crop(image, boxes, params, rng)

    if key == "brightness":
        range_pct = _float_param(params, "range_pct", 20.0)
        beta = float(rng.uniform(-range_pct, range_pct) * 255.0 / 100.0)
        return cv2.convertScaleAbs(image, alpha=1.0, beta=beta), boxes

    if key == "contrast":
        range_pct = _float_param(params, "range_pct", 20.0)
        alpha = float(rng.uniform(1.0 - range_pct / 100.0, 1.0 + range_pct / 100.0))
        return cv2.convertScaleAbs(image, alpha=max(0.01, alpha), beta=0), boxes

    if key == "saturation":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        range_pct = _float_param(params, "range_pct", 30.0)
        factor = float(rng.uniform(1.0 - range_pct / 100.0, 1.0 + range_pct / 100.0))
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * max(0.0, factor), 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR), boxes

    if key == "hue":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        max_shift = _float_param(params, "max_shift", 10.0)
        hsv[:, :, 0] = (hsv[:, :, 0] + rng.uniform(-max_shift, max_shift)) % 180
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR), boxes

    if key == "grayscale":
        if not _passes_prob(params, rng):
            return image, boxes
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), boxes

    if key == "blur":
        max_kernel = max(1, _int_param(params, "max_kernel", 3))
        if max_kernel % 2 == 0:
            max_kernel -= 1
        kernel = int(rng.integers(1, max_kernel + 1))
        if kernel % 2 == 0:
            kernel += 1
        kernel = max(1, kernel)
        if kernel <= 1:
            return image, boxes
        return cv2.GaussianBlur(image, (kernel, kernel), 0), boxes

    if key == "noise":
        max_sigma = _float_param(params, "max_sigma", 10.0)
        sigma = float(rng.uniform(0.0, max_sigma))
        noise = rng.normal(0.0, sigma, image.shape).astype(np.float32)
        noisy = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        return noisy, boxes

    if key == "cutout":
        return _cutout(image, boxes, params, rng), boxes

    return image, boxes


def _passes_prob(params: dict, rng: np.random.Generator) -> bool:
    return bool(rng.random() <= _float_param(params, "prob", 0.5))


def _float_param(params: dict, key: str, default: float) -> float:
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError):
        return default


def _int_param(params: dict, key: str, default: int) -> int:
    try:
        return int(round(float(params.get(key, default))))
    except (TypeError, ValueError):
        return default


def _rotation_matrix(image: np.ndarray, angle: float) -> np.ndarray:
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    return cv2.getRotationMatrix2D(center, angle, 1.0).astype(np.float32)


def _warp_with_matrix(
    image: np.ndarray,
    boxes: List[YoloBox],
    matrix: np.ndarray,
) -> Tuple[np.ndarray, List[YoloBox]]:
    height, width = image.shape[:2]
    warped = cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    transformed = [_transform_bbox(box, matrix, width, height) for box in boxes]
    return warped, [box for box in transformed if box is not None]


def _transform_bbox(box: YoloBox, matrix: np.ndarray, width: int, height: int) -> Optional[YoloBox]:
    corners = _yolo_to_corners(box, width, height)
    if corners is None:
        return None
    ones = np.ones((4, 1), dtype=np.float32)
    points = np.hstack([corners, ones])
    transformed = points @ matrix.T
    x1 = float(np.clip(np.min(transformed[:, 0]), 0, width))
    y1 = float(np.clip(np.min(transformed[:, 1]), 0, height))
    x2 = float(np.clip(np.max(transformed[:, 0]), 0, width))
    y2 = float(np.clip(np.max(transformed[:, 1]), 0, height))
    return _xyxy_to_yolo(box[0], x1, y1, x2, y2, width, height)


def _random_crop(
    image: np.ndarray,
    boxes: List[YoloBox],
    params: dict,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, List[YoloBox]]:
    height, width = image.shape[:2]
    min_area_pct = np.clip(_float_param(params, "min_area_pct", 80.0), 1.0, 100.0)
    area_pct = float(rng.uniform(min_area_pct, 100.0))
    scale = math.sqrt(area_pct / 100.0)
    crop_w = int(np.clip(round(width * scale), 1, width))
    crop_h = int(np.clip(round(height * scale), 1, height))
    left = int(rng.integers(0, max(1, width - crop_w + 1)))
    top = int(rng.integers(0, max(1, height - crop_h + 1)))
    right = left + crop_w
    bottom = top + crop_h

    cropped = image[top:bottom, left:right]
    resized = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)

    next_boxes: List[YoloBox] = []
    for box in boxes:
        corners = _yolo_to_corners(box, width, height)
        if corners is None:
            continue
        x1, y1 = float(np.min(corners[:, 0])), float(np.min(corners[:, 1]))
        x2, y2 = float(np.max(corners[:, 0])), float(np.max(corners[:, 1]))
        original_area = max(0.0, (x2 - x1) * (y2 - y1))
        clipped_x1 = float(np.clip(x1, left, right))
        clipped_y1 = float(np.clip(y1, top, bottom))
        clipped_x2 = float(np.clip(x2, left, right))
        clipped_y2 = float(np.clip(y2, top, bottom))
        clipped_area = max(0.0, (clipped_x2 - clipped_x1) * (clipped_y2 - clipped_y1))
        if original_area <= 0 or clipped_area < original_area * 0.10:
            continue
        nx1 = (clipped_x1 - left) * width / crop_w
        ny1 = (clipped_y1 - top) * height / crop_h
        nx2 = (clipped_x2 - left) * width / crop_w
        ny2 = (clipped_y2 - top) * height / crop_h
        converted = _xyxy_to_yolo(box[0], nx1, ny1, nx2, ny2, width, height)
        if converted is not None:
            next_boxes.append(converted)
    return resized, next_boxes


def _cutout(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> np.ndarray:
    _ = boxes
    height, width = image.shape[:2]
    output = image.copy()
    num_patches = max(1, _int_param(params, "num_patches", 3))
    max_size_pct = np.clip(_float_param(params, "max_size_pct", 15.0), 1.0, 100.0)
    for _idx in range(num_patches):
        patch_w = int(rng.integers(1, max(2, int(width * max_size_pct / 100.0) + 1)))
        patch_h = int(rng.integers(1, max(2, int(height * max_size_pct / 100.0) + 1)))
        left = int(rng.integers(0, max(1, width - patch_w + 1)))
        top = int(rng.integers(0, max(1, height - patch_h + 1)))
        output[top : top + patch_h, left : left + patch_w] = 0
    return output


def _yolo_to_corners(box: Sequence[Any], width: int, height: int) -> Optional[np.ndarray]:
    if len(box) != 5 or width <= 0 or height <= 0:
        return None
    try:
        cx = float(box[1]) * width
        cy = float(box[2]) * height
        bw = float(box[3]) * width
        bh = float(box[4]) * height
    except (TypeError, ValueError):
        return None
    if bw <= 0 or bh <= 0:
        return None
    x1 = cx - bw / 2.0
    y1 = cy - bh / 2.0
    x2 = cx + bw / 2.0
    y2 = cy + bh / 2.0
    return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)


def _xyxy_to_yolo(
    class_id: Any,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    width: int,
    height: int,
) -> Optional[YoloBox]:
    x1 = float(np.clip(x1, 0, width))
    y1 = float(np.clip(y1, 0, height))
    x2 = float(np.clip(x2, 0, width))
    y2 = float(np.clip(y2, 0, height))
    if x2 <= x1 or y2 <= y1:
        return None
    norm_w = (x2 - x1) / float(width)
    norm_h = (y2 - y1) / float(height)
    if norm_w <= 0.0 or norm_h <= 0.0:
        return None
    cx = (x1 + x2) / 2.0 / float(width)
    cy = (y1 + y2) / 2.0 / float(height)
    return [
        class_id,
        float(np.clip(cx, 0.0, 1.0)),
        float(np.clip(cy, 0.0, 1.0)),
        float(np.clip(norm_w, 0.0, 1.0)),
        float(np.clip(norm_h, 0.0, 1.0)),
    ]


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
