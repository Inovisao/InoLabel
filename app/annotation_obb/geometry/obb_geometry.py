from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Optional, Tuple

import numpy as np


@dataclass
class OBBDetection:
    cx: float
    cy: float
    width: float
    height: float
    angle: float
    category_id: int
    confidence: float = 1.0
    source: str = "manual"
    internal_id: Optional[int] = None
    track_id: Optional[int] = None


def clone_obb(det: OBBDetection) -> OBBDetection:
    return replace(det)


def obb_to_points(cx: float, cy: float, w: float, h: float, angle_deg: float) -> np.ndarray:
    theta = math.radians(angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    local = np.array(
        [
            [-w / 2.0, -h / 2.0],
            [w / 2.0, -h / 2.0],
            [w / 2.0, h / 2.0],
            [-w / 2.0, h / 2.0],
        ],
        dtype=np.float32,
    )
    rotation = np.array([[cos_t, -sin_t], [sin_t, cos_t]], dtype=np.float32)
    points = local @ rotation.T
    points[:, 0] += cx
    points[:, 1] += cy
    return points.astype(np.float32)


def points_to_hbb(points: np.ndarray) -> Tuple[float, float, float, float]:
    pts = np.asarray(points, dtype=np.float32)
    x_min = float(np.min(pts[:, 0]))
    y_min = float(np.min(pts[:, 1]))
    x_max = float(np.max(pts[:, 0]))
    y_max = float(np.max(pts[:, 1]))
    return x_min, y_min, x_max - x_min, y_max - y_min


def hbb_to_obb(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    category_id: int = 1,
    confidence: float = 1.0,
    source: str = "manual",
) -> OBBDetection:
    return OBBDetection(
        cx=float(x) + float(w) / 2.0,
        cy=float(y) + float(h) / 2.0,
        width=float(w),
        height=float(h),
        angle=0.0,
        category_id=int(category_id),
        confidence=float(confidence),
        source=source,
    )


def global_to_local(px: float, py: float, cx: float, cy: float, angle_deg: float) -> Tuple[float, float]:
    theta = math.radians(angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    dx = px - cx
    dy = py - cy
    return dx * cos_t + dy * sin_t, -dx * sin_t + dy * cos_t


def angle_from_mouse(cx: float, cy: float, mouse_x: float, mouse_y: float) -> float:
    dx = mouse_x - cx
    dy = mouse_y - cy
    return math.degrees(math.atan2(dy, dx)) + 90.0


def normalize_angle(angle: float) -> float:
    value = ((float(angle) + 180.0) % 360.0) - 180.0
    return 180.0 if value == -180.0 else value


def clip_obb_to_image(det: OBBDetection, img_w: int, img_h: int) -> OBBDetection:
    next_det = clone_obb(det)
    next_det.cx = float(np.clip(next_det.cx, 0, max(img_w - 1, 0)))
    next_det.cy = float(np.clip(next_det.cy, 0, max(img_h - 1, 0)))
    next_det.width = max(0.0, min(float(next_det.width), float(img_w)))
    next_det.height = max(0.0, min(float(next_det.height), float(img_h)))
    next_det.angle = normalize_angle(next_det.angle)
    return next_det


def validate_obb(det: OBBDetection, min_size: float = 3.0) -> bool:
    return det.width >= min_size and det.height >= min_size


def obb_area(det: OBBDetection) -> float:
    return float(max(det.width, 0.0) * max(det.height, 0.0))
