"""Utilitários de rotação visual para o canvas de anotação.

A rotação é puramente visual: não altera current_frame nem as coords
salvas. As funções aqui convertem coordenadas entre espaço original
e espaço rotacionado para que canvas_to_image_coords e
image_to_canvas_coords permaneçam corretos.
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
    """Retorna cópia rotacionada do frame (0/90/180/270 graus)."""
    code = _CV2_ROTATE.get(angle % 360)
    if code is None:
        return frame
    return cv2.rotate(frame, code)


def rotated_dims(orig_w: int, orig_h: int, angle: int) -> tuple[int, int]:
    """Dimensões (w, h) do frame após rotação."""
    if angle % 180 == 90:
        return orig_h, orig_w
    return orig_w, orig_h


def image_to_rotated(x: float, y: float, orig_w: int, orig_h: int, angle: int) -> tuple[float, float]:
    """Converte ponto do espaço original para espaço rotacionado."""
    a = angle % 360
    if a == 0:
        return x, y
    if a == 90:   # CW: (x,y) → (H-1-y, x)  novo_w=H, novo_h=W
        return orig_h - 1 - y, x
    if a == 180:  # (x,y) → (W-1-x, H-1-y)
        return orig_w - 1 - x, orig_h - 1 - y
    # 270 CW = 90 CCW: (x,y) → (y, W-1-x)  novo_w=H, novo_h=W
    return y, orig_w - 1 - x


def rotated_to_image(x: float, y: float, orig_w: int, orig_h: int, angle: int) -> tuple[float, float]:
    """Converte ponto do espaço rotacionado para espaço original (inversa)."""
    a = angle % 360
    if a == 0:
        return x, y
    if a == 90:   # inverso de CW: (rx,ry) → (ry, H-1-rx)
        return y, orig_h - 1 - x
    if a == 180:
        return orig_w - 1 - x, orig_h - 1 - y
    # inverso de 270 CW: (rx,ry) → (W-1-ry, rx)
    return orig_w - 1 - y, x
