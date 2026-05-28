"""Flet: eventos de mouse OBB — GestureDetector."""

from __future__ import annotations

from typing import Optional, Tuple

import flet as ft
import numpy as np

from app.annotation.ui.rotation_utils import rotated_dims, rotated_to_image
from app.annotation_obb.geometry.obb_geometry import (
    angle_from_mouse,
    global_to_local,
    hbb_to_obb,
    normalize_angle,
    obb_to_points,
    points_to_hbb,
    validate_obb,
)


class FletOBBMouseEventsMixin:
    """Substitui OBBMouseEventsMixin para Flet (GestureDetector)."""

    def _on_flet_mouse_down(self, e: ft.TapEvent):
        if self.current_frame is None:
            return
        x_canvas, y_canvas = int(e.local_x), int(e.local_y)

        if self.pan_mode:
            self._pan_start_x = x_canvas
            self._pan_start_y = y_canvas
            self._pan_start_offset_x = self.zoom_pan_x
            self._pan_start_offset_y = self.zoom_pan_y
            return

        img_coords = self.canvas_to_image_coords(x_canvas, y_canvas)
        if img_coords is None:
            return
        x, y = img_coords

        if self.roi_capture_mode and not self.roi_defined:
            self.add_roi_point(x, y)
            return
        if self.remove_mode:
            self.remove_annotation_at(x, y)
            return
        if self.selection_mode:
            self.select_detection_at(x, y)
            return

        rotate_hit = self._hit_rotate_handle(x, y)
        if rotate_hit is not None:
            self.push_undo_state("rotacionar OBB")
            self.selected_obb = rotate_hit
            self.selected_detection = rotate_hit
            self.obb_interaction_mode = "rotate"
            det = self.get_selected_detection()
            self.rotate_start_angle = angle_from_mouse(det.cx, det.cy, x, y) if det is not None else None
            return

        body_hit = self.find_detection_at(x, y)
        if body_hit is not None:
            self.push_undo_state("mover OBB")
            self.selected_obb = body_hit
            self.selected_detection = body_hit
            self.obb_interaction_mode = "move"
            self.drag_start = (x, y)
            return

        if not self.annotation_mode:
            return

        self.obb_interaction_mode = "draw"
        self.drawing_start = (x, y)
        self.drag_start = (x, y)
        self.drawing_rect_id = True
        self._drawing_canvas_start = (x_canvas, y_canvas)
        self._show_drawing_rect(x_canvas, y_canvas, x_canvas, y_canvas)

    def _on_flet_secondary_down(self, e: ft.TapEvent):
        if self.current_frame is None:
            return
        self._pan_start_x = int(e.local_x)
        self._pan_start_y = int(e.local_y)
        self._pan_start_offset_x = self.zoom_pan_x
        self._pan_start_offset_y = self.zoom_pan_y

    def _on_flet_pan_end(self, e: ft.TapEvent):
        self._pan_start_x = None

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

        img_coords = self._canvas_to_image_clamped(x_canvas, y_canvas)
        if img_coords is None:
            return
        x, y = img_coords

        if self.obb_interaction_mode == "draw" and self.drawing_start is not None:
            start_cx, start_cy = self._drawing_canvas_start
            self._show_drawing_rect(start_cx, start_cy, x_canvas, y_canvas)
            return

        det = self.get_selected_detection()
        if det is None:
            return

        if self.obb_interaction_mode == "move" and self.drag_start is not None:
            prev_x, prev_y = self.drag_start
            det.cx += x - prev_x
            det.cy += y - prev_y
            self.drag_start = (x, y)
            self.update_display(refresh_status=True)
            return

        if self.obb_interaction_mode == "rotate":
            det.angle = normalize_angle(angle_from_mouse(det.cx, det.cy, x, y))
            self.update_display(refresh_status=True)

    def _on_flet_mouse_up(self, e: ft.TapEvent):
        if self.current_frame is None:
            return
        x_canvas = int(e.local_x)
        y_canvas = int(e.local_y)

        if self.pan_mode:
            self._pan_start_x = None
            return

        if self.obb_interaction_mode == "draw" and self.drawing_start is not None:
            self._finish_obb_draw(x_canvas, y_canvas)

        self.obb_interaction_mode = None
        self.drag_start = None
        self.rotate_start_angle = None
        self._hide_drawing_rect()
        self.drawing_rect_id = None
        self.drawing_start = None
        self.update_display(refresh_status=True)

    def _finish_obb_draw(self, x_canvas: int, y_canvas: int):
        start_x, start_y = self.drawing_start
        end_coords = self._canvas_to_image_clamped(x_canvas, y_canvas)
        if end_coords is None:
            return
        end_x, end_y = end_coords
        x1, x2 = sorted((start_x, end_x))
        y1, y2 = sorted((start_y, end_y))
        det = hbb_to_obb(x1, y1, x2 - x1, y2 - y1, category_id=self.active_category_id(), source="manual")
        if not validate_obb(det):
            return
        points = obb_to_points(det.cx, det.cy, det.width, det.height, det.angle)
        hx, hy, hw, hh = points_to_hbb(points)
        if not self.is_inside_roi(np.array([hx, hy, hx + hw, hy + hh], dtype=np.float32)):
            print("[INFO] OBB manual ignorada pois esta fora do ROI.")
            return
        self.push_undo_state("adicionar OBB manual")
        self.manual_obb_detections.append(det)
        self.manual_detections = self.manual_obb_detections
        self.selected_obb = ("manual", len(self.manual_obb_detections) - 1)
        self.selected_detection = self.selected_obb

    def _canvas_to_image_clamped(self, x_canvas: int, y_canvas: int) -> Optional[Tuple[int, int]]:
        coords = self.canvas_to_image_coords(x_canvas, y_canvas)
        if coords is not None:
            return coords
        if self.current_frame is None:
            return None
        orig_h, orig_w = self.current_frame.shape[:2]
        rotation = getattr(self, "frame_rotation", 0)
        rot_w, rot_h = rotated_dims(orig_w, orig_h, rotation)
        rx = int(np.clip((x_canvas - self.offset_x) / max(self.display_scale, 1e-9), 0, rot_w - 1))
        ry = int(np.clip((y_canvas - self.offset_y) / max(self.display_scale, 1e-9), 0, rot_h - 1))
        if rotation:
            ox, oy = rotated_to_image(rx, ry, orig_w, orig_h, rotation)
            return int(np.clip(ox, 0, orig_w - 1)), int(np.clip(oy, 0, orig_h - 1))
        return rx, ry

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

    def update_canvas_cursor(self):
        cursor = ft.MouseCursor.MOVE if getattr(self, "pan_mode", False) else ft.MouseCursor.PRECISE
        try:
            self._flet_gesture.mouse_cursor = cursor
            self.page.update()
        except Exception:  # pylint: disable=broad-except
            pass

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

    def remove_annotation_at(self, x: int, y: int) -> bool:
        for source, dets in (("manual", self.manual_obb_detections), ("model", self.current_obb_detections)):
            for idx in range(len(dets) - 1, -1, -1):
                det = dets[idx]
                lx, ly = global_to_local(x, y, det.cx, det.cy, det.angle)
                if abs(lx) <= det.width / 2.0 and abs(ly) <= det.height / 2.0:
                    self.push_undo_state("remover OBB")
                    del dets[idx]
                    self.current_detections = self.current_obb_detections
                    self.manual_detections = self.manual_obb_detections
                    self.selected_obb = None
                    self.selected_detection = None
                    print(f"[INFO] OBB {source} removida.")
                    self.update_display(refresh_status=True)
                    return True
        print("[INFO] Nenhuma OBB encontrada para remover.")
        return False
