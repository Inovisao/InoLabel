"""Matematica pura de coordenadas e zoom/pan — sem dependencias de UI."""

from __future__ import annotations

import numpy as np

from backend.annotation.ui.rotation_utils import rotated_dims, rotated_to_image


class DisplayCanvasMixin:
    def image_to_canvas_coords(self, x: float, y: float):
        rotation = getattr(self, "frame_rotation", 0)
        if rotation and self.current_frame is not None:
            orig_h, orig_w = self.current_frame.shape[:2]
            from backend.annotation.ui.rotation_utils import image_to_rotated
            x, y = image_to_rotated(x, y, orig_w, orig_h, rotation)
        cx = int(round(x * self.display_scale + self.offset_x))
        cy = int(round(y * self.display_scale + self.offset_y))
        return cx, cy

    def canvas_to_image_coords(self, canvas_x: int, canvas_y: int):
        if self.current_frame is None:
            return None
        orig_h, orig_w = self.current_frame.shape[:2]
        rotation = getattr(self, "frame_rotation", 0)
        rot_w, rot_h = rotated_dims(orig_w, orig_h, rotation)
        x = (canvas_x - self.offset_x) / max(self.display_scale, 1e-9)
        y = (canvas_y - self.offset_y) / max(self.display_scale, 1e-9)
        if x < 0 or y < 0 or x >= rot_w or y >= rot_h:
            return None
        rx = int(np.clip(x, 0, rot_w - 1))
        ry = int(np.clip(y, 0, rot_h - 1))
        if rotation:
            ox, oy = rotated_to_image(rx, ry, orig_w, orig_h, rotation)
            return int(np.clip(ox, 0, orig_w - 1)), int(np.clip(oy, 0, orig_h - 1))
        return rx, ry

    def clamp_zoom_pan(
        self,
        disp_w: int,
        disp_h: int,
        canvas_w: int,
        canvas_h: int,
        base_offset_x: int,
        base_offset_y: int,
    ) -> None:
        if disp_w <= canvas_w:
            self.zoom_pan_x = 0
        else:
            self.zoom_pan_x = int(np.clip(
                self.zoom_pan_x,
                canvas_w - disp_w - base_offset_x,
                -base_offset_x,
            ))
        if disp_h <= canvas_h:
            self.zoom_pan_y = 0
        else:
            self.zoom_pan_y = int(np.clip(
                self.zoom_pan_y,
                canvas_h - disp_h - base_offset_y,
                -base_offset_y,
            ))
