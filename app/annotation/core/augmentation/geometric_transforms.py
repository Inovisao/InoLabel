"""Transformações geométricas: mexem na imagem e nas caixas (flip, rotação, cisalhamento, recorte)."""

from __future__ import annotations

import math
from typing import Any, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from app.annotation.core.augmentation.params import float_param, passes_prob

YoloBox = List[Any]
Transformed = Tuple[np.ndarray, List[YoloBox]]


def flip_h(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    if not passes_prob(params, rng):
        return image, boxes
    flipped = cv2.flip(image, 1)
    return flipped, [[box[0], 1.0 - float(box[1]), box[2], box[3], box[4]] for box in boxes]


def flip_v(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    if not passes_prob(params, rng):
        return image, boxes
    flipped = cv2.flip(image, 0)
    return flipped, [[box[0], box[1], 1.0 - float(box[2]), box[3], box[4]] for box in boxes]


def rotate(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    if not passes_prob(params, rng):
        return image, boxes
    max_degrees = float_param(params, "max_degrees", 15.0)
    angle = float(rng.uniform(-max_degrees, max_degrees))
    return warp_with_matrix(image, boxes, rotation_matrix(image, angle))


def shear(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    if not passes_prob(params, rng):
        return image, boxes
    max_degrees = float_param(params, "max_degrees", 10.0)
    angle = float(rng.uniform(-max_degrees, max_degrees))
    shear = math.tan(math.radians(angle))
    height = image.shape[0]
    # x' = x + shear * (y - h/2): cisalha em torno do centro vertical da imagem.
    matrix = np.array([[1.0, shear, -shear * height / 2.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    return warp_with_matrix(image, boxes, matrix)


def crop(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    if not passes_prob(params, rng):
        return image, boxes
    return random_crop(image, boxes, params, rng)



# ── auxiliares ──

def rotation_matrix(image: np.ndarray, angle: float) -> np.ndarray:
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    return cv2.getRotationMatrix2D(center, angle, 1.0).astype(np.float32)


def warp_with_matrix(
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
    transformed = [transform_bbox(box, matrix, width, height) for box in boxes]
    return warped, [box for box in transformed if box is not None]


def transform_bbox(box: YoloBox, matrix: np.ndarray, width: int, height: int) -> Optional[YoloBox]:
    corners = yolo_to_corners(box, width, height)
    if corners is None:
        return None
    ones = np.ones((4, 1), dtype=np.float32)
    points = np.hstack([corners, ones])
    transformed = points @ matrix.T
    x1 = float(np.clip(np.min(transformed[:, 0]), 0, width))
    y1 = float(np.clip(np.min(transformed[:, 1]), 0, height))
    x2 = float(np.clip(np.max(transformed[:, 0]), 0, width))
    y2 = float(np.clip(np.max(transformed[:, 1]), 0, height))
    return xyxy_to_yolo(box[0], x1, y1, x2, y2, width, height)


def random_crop(
    image: np.ndarray,
    boxes: List[YoloBox],
    params: dict,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, List[YoloBox]]:
    height, width = image.shape[:2]
    min_area_pct = np.clip(float_param(params, "min_area_pct", 80.0), 1.0, 100.0)
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
        corners = yolo_to_corners(box, width, height)
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
        converted = xyxy_to_yolo(box[0], nx1, ny1, nx2, ny2, width, height)
        if converted is not None:
            next_boxes.append(converted)
    return resized, next_boxes


def yolo_to_corners(box: Sequence[Any], width: int, height: int) -> Optional[np.ndarray]:
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


def xyxy_to_yolo(
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
