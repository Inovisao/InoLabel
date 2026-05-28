"""Flet: renderização do canvas — converte frame OpenCV → base64 → ft.Image."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.annotation.ui.rotation_utils import (
    apply_frame_rotation,
    image_to_rotated,
    rotated_dims,
    rotated_to_image,
)
from app.config import (
    CANVAS_PADDING_PX,
    SHOW_MANUAL_DETECTIONS,
    SHOW_MODEL_DETECTIONS,
    WINDOW_MARGIN_PX,
    WINDOW_TOP_RESERVED_PX,
)
from app.ui.theme.flet_theme import SIZES


class FletDisplayCanvasMixin:
    """Substitui DisplayCanvasMixin para renderização via Flet."""

    # ── Coordenadas ────────────────────────────────────────────────────────────

    def image_to_canvas_coords(self, x: float, y: float) -> Tuple[int, int]:
        rotation = getattr(self, "frame_rotation", 0)
        if rotation and self.current_frame is not None:
            orig_h, orig_w = self.current_frame.shape[:2]
            x, y = image_to_rotated(x, y, orig_w, orig_h, rotation)
        cx = int(round(x * self.display_scale + self.offset_x))
        cy = int(round(y * self.display_scale + self.offset_y))
        return cx, cy

    def canvas_to_image_coords(self, canvas_x: int, canvas_y: int) -> Optional[Tuple[int, int]]:
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

    # ── Viewport ───────────────────────────────────────────────────────────────

    def _canvas_viewport_limits(self) -> Tuple[int, int, int, int]:
        page = getattr(self, "page", None)
        if page is not None:
            try:
                screen_w = int(page.window.width or 1920)
                screen_h = int(page.window.height or 1080)
            except Exception:  # pylint: disable=broad-except
                screen_w, screen_h = 1920, 1080
        else:
            screen_w, screen_h = 1920, 1080

        available_w = max(320, screen_w - SIZES["sidebar_w"] - WINDOW_MARGIN_PX)
        available_h = max(240, screen_h - SIZES["topbar_h"] - SIZES["statusbar_h"] - WINDOW_TOP_RESERVED_PX)
        return available_w, available_h, screen_w, screen_h

    def clamp_zoom_pan(self, disp_w, disp_h, canvas_w, canvas_h, base_offset_x, base_offset_y):
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

    # ── Renderização principal ─────────────────────────────────────────────────

    def update_display(self, *, refresh_status: bool = False):
        if self.current_frame is None:
            return

        annotated = self.current_frame.copy()
        annotated = self._draw_roi_overlay_on_frame(annotated)
        self.validate_selected_detection()

        if SHOW_MODEL_DETECTIONS:
            annotated = self.draw_detections(annotated, self.current_detections, "model")
        if SHOW_MANUAL_DETECTIONS:
            annotated = self.draw_detections(annotated, self.manual_detections, "manual")

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

    def _compute_display_size(self, frame_w: int, frame_h: int, max_w: int, max_h: int) -> Tuple[int, int]:
        fit_scale = min(1.0, max_w / max(frame_w, 1), max_h / max(frame_h, 1))
        self.display_scale = fit_scale * self.zoom_scale
        return max(1, int(round(frame_w * self.display_scale))), max(1, int(round(frame_h * self.display_scale)))

    def _render_frame_on_canvas(self, frame, disp_w, disp_h, max_canvas_w, max_canvas_h, screen_w, screen_h):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        buf = BytesIO()
        pil_img.save(buf, format="JPEG", quality=88, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()

        canvas_w = min(max_canvas_w, disp_w + CANVAS_PADDING_PX)
        canvas_h = min(max_canvas_h, disp_h + CANVAS_PADDING_PX)
        base_offset_x = (canvas_w - disp_w) // 2
        base_offset_y = (canvas_h - disp_h) // 2
        self.clamp_zoom_pan(disp_w, disp_h, canvas_w, canvas_h, base_offset_x, base_offset_y)
        self.offset_x = base_offset_x + self.zoom_pan_x
        self.offset_y = base_offset_y + self.zoom_pan_y

        self._canvas_w = canvas_w
        self._canvas_h = canvas_h

        img = self._flet_canvas_image
        img.src_base64 = b64
        img.width = disp_w
        img.height = disp_h

        wrapper = self._flet_image_wrapper
        wrapper.left = float(self.offset_x)
        wrapper.top = float(self.offset_y)

        stack = self._flet_canvas_stack
        stack.width = canvas_w
        stack.height = canvas_h

        self.page.update()

    # ── Overlays — no-op Flet (já desenhados no frame via OpenCV) ─────────────

    def _draw_roi_overlay_on_canvas(self):
        pass

    def _draw_active_manual_rectangle(self):
        # Gerenciado diretamente pelo FletMouseEventsMixin via _flet_drawing_rect
        pass

    # ── Override de compat: _config_if_changed para widgets Flet ──────────────

    @staticmethod
    def _config_if_changed(widget, **kwargs):
        for key, value in kwargs.items():
            if key == "fg" or key == "foreground":
                if hasattr(widget, "color") and widget.color != value:
                    widget.color = value
            elif key == "state":
                disabled = str(value).lower() in ("disabled", "0")
                if hasattr(widget, "disabled") and widget.disabled != disabled:
                    widget.disabled = disabled
            elif key == "text":
                if hasattr(widget, "value") and widget.value != value:
                    widget.value = value
