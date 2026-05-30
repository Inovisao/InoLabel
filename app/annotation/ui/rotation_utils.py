"""Visual rotation utilities for the annotation canvas.

Rotation is purely visual: it does not modify current_frame or saved
coordinates. The functions here convert coordinates between the original
and rotated spaces so that canvas_to_image_coords and
image_to_canvas_coords remain correct.
"""

from __future__ import annotations

import cv2
import numpy as np

_CV2_ROTATE = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def apply_frame_rotation(frame: np.ndarray, angle: int) -> np.ndarray:
    """Returns a rotated copy of the frame (0/90/180/270 degrees)."""
    code = _CV2_ROTATE.get(angle % 360)
    if code is None:
        return frame
    return cv2.rotate(frame, code)


def rotated_dims(orig_w: int, orig_h: int, angle: int) -> tuple[int, int]:
    """Dimensions (w, h) of the frame after rotation."""
    if angle % 180 == 90:
        return orig_h, orig_w
    return orig_w, orig_h


def image_to_rotated(x: float, y: float, orig_w: int, orig_h: int, angle: int) -> tuple[float, float]:
    """Converts a point from the original space to the rotated space."""
    a = angle % 360
    if a == 0:
        return x, y
    if a == 90:   # CW: (x,y) → (H-1-y, x)  new_w=H, new_h=W
        return orig_h - 1 - y, x
    if a == 180:  # (x,y) → (W-1-x, H-1-y)
        return orig_w - 1 - x, orig_h - 1 - y
    # 270 CW = 90 CCW: (x,y) → (y, W-1-x)  new_w=H, new_h=W
    return y, orig_w - 1 - x


def rotated_to_image(x: float, y: float, orig_w: int, orig_h: int, angle: int) -> tuple[float, float]:
    """Converts a point from the rotated space back to the original space (inverse)."""
    a = angle % 360
    if a == 0:
        return x, y
    if a == 90:   # inverse of CW: (rx,ry) → (ry, H-1-rx)
        return y, orig_h - 1 - x
    if a == 180:
        return orig_w - 1 - x, orig_h - 1 - y
    # inverse of 270 CW: (rx,ry) → (W-1-ry, rx)
    return orig_w - 1 - y, x
