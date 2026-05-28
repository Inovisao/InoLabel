"""Flet: canvas OBB — renderização com detecções orientadas."""

from __future__ import annotations

import cv2

from app.annotation.flet_ui.display import FletDisplayCanvasMixin
from app.annotation.ui.rotation_utils import apply_frame_rotation
from app.config import SHOW_MANUAL_DETECTIONS, SHOW_MODEL_DETECTIONS


class FletOBBDisplayCanvasMixin(FletDisplayCanvasMixin):
    """Substitui OBBDisplayCanvasMixin + DisplayCanvasMixin para Flet."""

    def update_display(self, *, refresh_status: bool = False):
        if self.current_frame is None:
            return
        annotated = self.current_frame.copy()
        annotated = self._draw_roi_overlay_on_frame(annotated)
        self.validate_selected_detection()
        if SHOW_MODEL_DETECTIONS:
            annotated = self.draw_obb_detections(annotated, self.current_obb_detections, "model")
        if SHOW_MANUAL_DETECTIONS:
            annotated = self.draw_obb_detections(annotated, self.manual_obb_detections, "manual")
        rotation = getattr(self, "frame_rotation", 0)
        if rotation:
            annotated = apply_frame_rotation(annotated, rotation)
        frame_h, frame_w = annotated.shape[:2]
        max_canvas_w, max_canvas_h, screen_w, screen_h = self._canvas_viewport_limits()
        disp_w, disp_h = self._compute_display_size(frame_w, frame_h, max_canvas_w, max_canvas_h)
        if disp_w != frame_w or disp_h != frame_h:
            interp = cv2.INTER_AREA if self.display_scale < 1.0 else cv2.INTER_LINEAR
            annotated = cv2.resize(annotated, (disp_w, disp_h), interpolation=interp)
        self._render_frame_on_canvas(annotated, disp_w, disp_h, max_canvas_w, max_canvas_h, screen_w, screen_h)
        self.last_frame_shape = (frame_w, frame_h)
        if refresh_status:
            self.update_status()
