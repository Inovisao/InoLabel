"""Flet: eventos de mouse via GestureDetector."""

from __future__ import annotations

from typing import Optional, Tuple

import flet as ft
import numpy as np

from app.annotation.ui.rotation_utils import rotated_dims, rotated_to_image
from app.models import Detection


class FletMouseEventsMixin:
    """Substitui MouseEventsMixin para Flet (GestureDetector)."""

    # ── Tap down (equivalente a ButtonPress-1) ─────────────────────────────────

    def _on_flet_mouse_down(self, e: ft.TapEvent):
        if self.current_frame is None:
            return
        x_canvas, y_canvas = int(e.local_x), int(e.local_y)

        if self.pan_mode:
            self._pan_start_x = x_canvas
            self._pan_start_y = y_canvas
            self._pan_start_offset_x = self.zoom_pan_x
            self._pan_start_offset_y = self.zoom_pan_y
            self._update_cursor("move")
            return

        img_coords = self.canvas_to_image_coords(x_canvas, y_canvas)
        if img_coords is None:
            return
        x, y = img_coords

        if self.roi_capture_mode and not self.roi_defined:
            self.add_roi_point(x, y)
            return
        if self.edit_id_mode or self.selection_mode:
            self.select_detection_at(x, y)
            return
        if self.remove_mode:
            self.remove_annotation_at(x, y)
            return
        if not self.annotation_mode:
            return

        self.drawing_start = (x, y)
        self._drawing_canvas_start = (x_canvas, y_canvas)
        self.drawing_rect_id = True  # flag "em progresso"
        self._show_drawing_rect(x_canvas, y_canvas, x_canvas, y_canvas)

    # ── Pan drag (secondary / middle button) ──────────────────────────────────

    def _on_flet_secondary_down(self, e: ft.TapEvent):
        if self.current_frame is None:
            return
        self._pan_start_x = int(e.local_x)
        self._pan_start_y = int(e.local_y)
        self._pan_start_offset_x = self.zoom_pan_x
        self._pan_start_offset_y = self.zoom_pan_y
        self._update_cursor("move")

    def _on_flet_pan_end(self, e: ft.TapEvent):
        self._pan_start_x = None
        self._update_cursor("crosshair")

    # ── Drag (equivalente a B1-Motion) ────────────────────────────────────────

    def _on_flet_mouse_drag(self, e: ft.DragUpdateDetails):
        if self.current_frame is None:
            return
        x_canvas = int(e.local_x)
        y_canvas = int(e.local_y)

        if self.pan_mode or getattr(self, "_pan_start_x", None) is not None:
            if getattr(self, "_pan_start_x", None) is not None:
                dx = x_canvas - self._pan_start_x
                dy = y_canvas - self._pan_start_y
                self.zoom_pan_x = self._pan_start_offset_x + dx
                self.zoom_pan_y = self._pan_start_offset_y + dy
                self.update_display()
            return

        if not self.annotation_mode or self.drawing_start is None:
            return

        start_cx, start_cy = self._drawing_canvas_start
        self._show_drawing_rect(start_cx, start_cy, x_canvas, y_canvas)

    # ── Tap up (equivalente a ButtonRelease-1) ─────────────────────────────────

    def _on_flet_mouse_up(self, e: ft.TapEvent):
        if self.current_frame is None:
            return
        x_canvas = int(e.local_x)
        y_canvas = int(e.local_y)

        if self.pan_mode:
            self._pan_start_x = None
            self._update_cursor("crosshair")
            return

        if not self.annotation_mode or self.drawing_start is None:
            return

        start_x, start_y = self.drawing_start
        end_coords = self.canvas_to_image_coords(x_canvas, y_canvas)
        if end_coords is None:
            orig_h, orig_w = self.current_frame.shape[:2]
            rotation = getattr(self, "frame_rotation", 0)
            rot_w, rot_h = rotated_dims(orig_w, orig_h, rotation)
            rx = int(np.clip((x_canvas - self.offset_x) / max(self.display_scale, 1e-9), 0, rot_w - 1))
            ry = int(np.clip((y_canvas - self.offset_y) / max(self.display_scale, 1e-9), 0, rot_h - 1))
            if rotation:
                ox, oy = rotated_to_image(rx, ry, orig_w, orig_h, rotation)
                end_x = int(np.clip(ox, 0, orig_w - 1))
                end_y = int(np.clip(oy, 0, orig_h - 1))
            else:
                end_x, end_y = rx, ry
        else:
            end_x, end_y = end_coords

        self._hide_drawing_rect()
        self.drawing_rect_id = None
        self.drawing_start = None

        x1, x2 = sorted((start_x, end_x))
        y1, y2 = sorted((start_y, end_y))
        if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
            return

        bbox = np.array([int(x1), int(y1), int(x2), int(y2)], dtype=np.float32)
        if not self.is_inside_roi(bbox):
            print("[INFO] Caixa fora do ROI — ignorada.")
            return
        self.push_undo_state("adicionar anotacao manual")

        track_id = None
        if self.tracking_enabled:
            track_id = self.consume_manual_id_override()
            if track_id is None:
                track_id = self.match_manual_to_history(bbox)
            if track_id is None:
                track_id = self.new_track_id()

        warp_bbox = None
        if self.homography_matrix is not None and self.warp_size is not None:
            warp_bbox = self.project_bbox(bbox, self.homography_matrix, self.warp_size[0], self.warp_size[1])

        manual_det = Detection(
            original_bbox=bbox,
            warp_bbox=warp_bbox,
            confidence=1.0,
            category_id=self.active_category_id(),
            track_id=track_id,
            source="manual",
        )
        self.manual_detections.append(manual_det)
        if track_id is not None:
            self.track_history.setdefault(track_id, []).append({"frame": self.frame_index, "bbox": bbox.tolist()})
            self.recent_tracks.append({"frame": self.frame_index, "tracks": [{"id": track_id, "bbox": bbox.copy()}]})
            if len(self.recent_tracks) > self.history_window:
                self.recent_tracks.pop(0)
        self.update_display(refresh_status=True)

    # ── Scroll / zoom ─────────────────────────────────────────────────────────

    def _on_flet_scroll(self, e: ft.ScrollEvent):
        if self.current_frame is None:
            return
        delta = e.scroll_delta_y
        factor = 1.1 if delta < 0 else 1 / 1.1
        new_zoom = max(0.2, min(8.0, self.zoom_scale * factor))
        if new_zoom == self.zoom_scale:
            return

        ex, ey = int(e.local_x), int(e.local_y)
        old_img_x = (ex - self.offset_x) / max(self.display_scale, 1e-9)
        old_img_y = (ey - self.offset_y) / max(self.display_scale, 1e-9)

        frame_h, frame_w = self.current_frame.shape[:2]
        max_canvas_w, max_canvas_h, _, _ = self._canvas_viewport_limits()
        fit_scale = min(1.0, max_canvas_w / max(frame_w, 1), max_canvas_h / max(frame_h, 1))
        new_display_scale = fit_scale * new_zoom
        new_disp_w = max(1, int(round(frame_w * new_display_scale)))
        new_disp_h = max(1, int(round(frame_h * new_display_scale)))
        new_canvas_w = min(max_canvas_w, new_disp_w + 80)
        new_canvas_h = min(max_canvas_h, new_disp_h + 80)
        base_x = (new_canvas_w - new_disp_w) // 2
        base_y = (new_canvas_h - new_disp_h) // 2

        new_offset_x = ex - old_img_x * new_display_scale
        new_offset_y = ey - old_img_y * new_display_scale

        self.zoom_scale = new_zoom
        self.zoom_pan_x = int(round(new_offset_x - base_x))
        self.zoom_pan_y = int(round(new_offset_y - base_y))
        self.clamp_zoom_pan(new_disp_w, new_disp_h, new_canvas_w, new_canvas_h, base_x, base_y)
        self.update_display()

    def reset_zoom(self):
        self.zoom_scale = 1.0
        self.zoom_pan_x = 0
        self.zoom_pan_y = 0
        self.update_display()

    # ── Remove / pan compat ────────────────────────────────────────────────────

    def remove_annotation_at(self, x: int, y: int) -> bool:
        for idx in range(len(self.manual_detections) - 1, -1, -1):
            det = self.manual_detections[idx]
            x1, y1, x2, y2 = det.original_bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.push_undo_state("remover anotacao manual")
                self.remove_detection_from_runtime_state(det)
                del self.manual_detections[idx]
                self.selected_detection = None
                self.update_display(refresh_status=True)
                return True
        for idx in range(len(self.current_detections) - 1, -1, -1):
            det = self.current_detections[idx]
            x1, y1, x2, y2 = det.original_bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.push_undo_state("remover deteccao")
                self.remove_detection_from_runtime_state(det)
                del self.current_detections[idx]
                self.selected_detection = None
                self.update_display(refresh_status=True)
                return True
        return False

    def update_canvas_cursor(self):
        cursor = ft.MouseCursor.MOVE if getattr(self, "pan_mode", False) else ft.MouseCursor.PRECISE
        try:
            self._flet_gesture.mouse_cursor = cursor
            self.page.update()
        except Exception:  # pylint: disable=broad-except
            pass

    # ── Overlay de retângulo ───────────────────────────────────────────────────

    def _show_drawing_rect(self, x0: int, y0: int, x1: int, y1: int):
        rx = min(x0, x1)
        ry = min(y0, y1)
        rw = max(1, abs(x1 - x0))
        rh = max(1, abs(y1 - y0))
        rect = self._flet_drawing_rect
        rect.left = float(rx)
        rect.top = float(ry)
        rect.width = float(rw)
        rect.height = float(rh)
        rect.visible = True
        self.page.update()

    def _hide_drawing_rect(self):
        self._flet_drawing_rect.visible = False
        self.page.update()

    def _update_cursor(self, cursor_type: str):
        mapping = {
            "move":      ft.MouseCursor.MOVE,
            "crosshair": ft.MouseCursor.PRECISE,
        }
        try:
            self._flet_gesture.mouse_cursor = mapping.get(cursor_type, ft.MouseCursor.PRECISE)
            self.page.update()
        except Exception:  # pylint: disable=broad-except
            pass
