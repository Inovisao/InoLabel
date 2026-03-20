from typing import Optional, Tuple

import numpy as np


def order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def destination_size(ordered_pts: np.ndarray) -> Tuple[int, int]:
    (tl, tr, br, bl) = ordered_pts
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    width = int(max(width_a, width_b))
    height = int(max(height_a, height_b))
    return max(width, 1), max(height, 1)


def clip_bbox(x1: float, y1: float, x2: float, y2: float, width: int, height: int) -> np.ndarray:
    x1_c = max(0.0, min(float(width - 1), x1))
    y1_c = max(0.0, min(float(height - 1), y1))
    x2_c = max(0.0, min(float(width - 1), x2))
    y2_c = max(0.0, min(float(height - 1), y2))
    return np.array([x1_c, y1_c, x2_c, y2_c], dtype=np.float32)


def bbox_iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
    xa1, ya1, xa2, ya2 = box_a
    xb1, yb1, xb2, yb2 = box_b
    inter_x1 = max(xa1, xb1)
    inter_y1 = max(ya1, yb1)
    inter_x2 = min(xa2, xb2)
    inter_y2 = min(ya2, yb2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, xa2 - xa1) * max(0.0, ya2 - ya1)
    area_b = max(0.0, xb2 - xb1) * max(0.0, yb2 - yb1)
    union = area_a + area_b - inter_area
    if union == 0:
        return 0.0
    return inter_area / union


def bbox_center(bbox: np.ndarray) -> Tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (float(x1 + x2) / 2.0, float(y1 + y2) / 2.0)


def parse_frame_number_from_name(file_name: str, video_stem: str) -> Optional[int]:
    prefix = f"{video_stem}_frame_"
    if not file_name.startswith(prefix):
        return None
    try:
        number_part = file_name[len(prefix) :].split(".")[0]
        return int(number_part)
    except Exception:
        return None
