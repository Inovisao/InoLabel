"""Transformações fotométricas: mexem só nos pixels; as caixas ficam iguais."""

from __future__ import annotations

from typing import Any, List, Tuple

import cv2
import numpy as np

from app.annotation.core.augmentation.params import float_param, int_param, passes_prob

YoloBox = List[Any]
Transformed = Tuple[np.ndarray, List[YoloBox]]


def brightness(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    range_pct = float_param(params, "range_pct", 20.0)
    beta = float(rng.uniform(-range_pct, range_pct) * 255.0 / 100.0)
    return cv2.convertScaleAbs(image, alpha=1.0, beta=beta), boxes


def contrast(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    range_pct = float_param(params, "range_pct", 20.0)
    alpha = float(rng.uniform(1.0 - range_pct / 100.0, 1.0 + range_pct / 100.0))
    return cv2.convertScaleAbs(image, alpha=max(0.01, alpha), beta=0), boxes


def saturation(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    range_pct = float_param(params, "range_pct", 30.0)
    factor = float(rng.uniform(1.0 - range_pct / 100.0, 1.0 + range_pct / 100.0))
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * max(0.0, factor), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR), boxes


def hue(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    max_shift = float_param(params, "max_shift", 10.0)
    hsv[:, :, 0] = (hsv[:, :, 0] + rng.uniform(-max_shift, max_shift)) % 180
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR), boxes


def grayscale(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    if not passes_prob(params, rng):
        return image, boxes
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), boxes


def blur(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    max_kernel = max(1, int_param(params, "max_kernel", 3))
    if max_kernel % 2 == 0:
        max_kernel -= 1
    kernel = int(rng.integers(1, max_kernel + 1))
    if kernel % 2 == 0:
        kernel += 1
    kernel = max(1, kernel)
    if kernel <= 1:
        return image, boxes
    return cv2.GaussianBlur(image, (kernel, kernel), 0), boxes


def noise(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    max_sigma = float_param(params, "max_sigma", 10.0)
    sigma = float(rng.uniform(0.0, max_sigma))
    noise = rng.normal(0.0, sigma, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy, boxes


def cutout(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> Transformed:
    return _cutout_mask(image, boxes, params, rng), boxes



def _cutout_mask(image: np.ndarray, boxes: List[YoloBox], params: dict, rng: np.random.Generator) -> np.ndarray:
    _ = boxes
    height, width = image.shape[:2]
    output = image.copy()
    num_patches = max(1, int_param(params, "num_patches", 3))
    max_size_pct = np.clip(float_param(params, "max_size_pct", 15.0), 1.0, 100.0)
    for _idx in range(num_patches):
        patch_w = int(rng.integers(1, max(2, int(width * max_size_pct / 100.0) + 1)))
        patch_h = int(rng.integers(1, max(2, int(height * max_size_pct / 100.0) + 1)))
        left = int(rng.integers(0, max(1, width - patch_w + 1)))
        top = int(rng.integers(0, max(1, height - patch_h + 1)))
        output[top : top + patch_h, left : left + patch_w] = 0
    return output
