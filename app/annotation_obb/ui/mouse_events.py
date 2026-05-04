from app.annotation_obb.shared import *


class OBBMouseEventsMixin:
    def on_mouse_down(self, event):
        if self.current_frame is None:
            return
        if self.pan_mode:
            self.on_pan_start(event)
            return "break"
        img_coords = self.canvas_to_image_coords(event.x, event.y)
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
        self.drawing_rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="yellow", width=2, dash=(4, 2))

    def on_mouse_drag(self, event):
        if self.pan_mode:
            self.on_pan_drag(event)
            return "break"
        img_coords = self._event_to_image_clamped(event)
        if img_coords is None:
            return
        x, y = img_coords
        if self.obb_interaction_mode == "draw" and self.drawing_start is not None:
            start_cx, start_cy = self.image_to_canvas_coords(self.drawing_start[0], self.drawing_start[1])
            if self.drawing_rect_id is not None:
                self.canvas.coords(self.drawing_rect_id, start_cx, start_cy, event.x, event.y)
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

    def on_mouse_up(self, event):
        if self.pan_mode:
            self.on_pan_end(event)
            return "break"
        if self.obb_interaction_mode == "draw" and self.drawing_start is not None:
            self._finish_draw(event)
        self.obb_interaction_mode = None
        self.drag_start = None
        self.rotate_start_angle = None
        if self.drawing_rect_id is not None:
            self.canvas.delete(self.drawing_rect_id)
            self.drawing_rect_id = None
        self.drawing_start = None
        self.update_display(refresh_status=True)

    def _finish_draw(self, event):
        start_x, start_y = self.drawing_start
        end_coords = self._event_to_image_clamped(event)
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

    def _event_to_image_clamped(self, event) -> Optional[Tuple[int, int]]:
        coords = self.canvas_to_image_coords(event.x, event.y)
        if coords is not None:
            return coords
        if self.current_frame is None:
            return None
        frame_h, frame_w = self.current_frame.shape[:2]
        x = int(np.clip((event.x - self.offset_x) / max(self.display_scale, 1e-9), 0, frame_w - 1))
        y = int(np.clip((event.y - self.offset_y) / max(self.display_scale, 1e-9), 0, frame_h - 1))
        return x, y

    def _hit_rotate_handle(self, x: int, y: int) -> Optional[Tuple[str, int]]:
        for source, dets in (("manual", self.manual_obb_detections), ("model", self.current_obb_detections)):
            for idx in range(len(dets) - 1, -1, -1):
                hx, hy = self.rotation_handle_image_pos(dets[idx])
                if math.hypot(x - hx, y - hy) <= 12.0 / max(self.display_scale, 1e-9):
                    return source, idx
        return None

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

    def on_pan_start(self, event):
        if self.current_frame is None:
            return
        self.pan_drag_start = (event.x, event.y)
        self.pan_start_offset = (self.zoom_pan_x, self.zoom_pan_y)
        try:
            self.canvas.config(cursor="fleur")
        except Exception:  # pylint: disable=broad-except
            pass

    def on_pan_drag(self, event):
        if self.current_frame is None or self.pan_drag_start is None:
            return
        start_x, start_y = self.pan_drag_start
        start_pan_x, start_pan_y = self.pan_start_offset
        self.zoom_pan_x = start_pan_x + int(event.x - start_x)
        self.zoom_pan_y = start_pan_y + int(event.y - start_y)
        self.update_display()

    def on_pan_end(self, _event):
        self.pan_drag_start = None
        self.update_canvas_cursor()

    def update_canvas_cursor(self):
        cursor = "fleur" if self.pan_mode else "crosshair"
        try:
            self.canvas.config(cursor=cursor)
        except Exception:  # pylint: disable=broad-except
            pass

    def toggle_pan_mode(self):
        self.pan_mode = not self.pan_mode
        if self.pan_mode:
            self.annotation_mode = False
            self.remove_mode = False
            self.selection_mode = False
        self.pan_drag_start = None
        self.update_annotation_button()
        self.update_remove_button()
        self.update_selection_button()
        self.update_pan_button()
        self.update_canvas_cursor()
        self.info_var.set("Pan ON: arraste a imagem para mover." if self.pan_mode else "Pan OFF.")
        self.update_status()

    def on_zoom(self, event):
        if self.current_frame is None:
            return
        event_delta = getattr(event, "delta", 0)
        event_num = getattr(event, "num", None)
        if event_delta != 0:
            factor = 1.1 if event_delta > 0 else 1 / 1.1
        elif event_num == 4:
            factor = 1.1
        elif event_num == 5:
            factor = 1 / 1.1
        else:
            return
        new_zoom = max(0.2, min(8.0, self.zoom_scale * factor))
        if new_zoom == self.zoom_scale:
            return
        old_img_x = (event.x - self.offset_x) / max(self.display_scale, 1e-9)
        old_img_y = (event.y - self.offset_y) / max(self.display_scale, 1e-9)
        frame_h, frame_w = self.current_frame.shape[:2]
        max_canvas_w, max_canvas_h, _, _ = self._canvas_viewport_limits()
        fit_scale = min(1.0, max_canvas_w / frame_w, max_canvas_h / frame_h)
        new_display_scale = fit_scale * new_zoom
        new_disp_w = max(1, int(round(frame_w * new_display_scale)))
        new_disp_h = max(1, int(round(frame_h * new_display_scale)))
        new_canvas_w = min(max_canvas_w, new_disp_w + CANVAS_PADDING_PX)
        new_canvas_h = min(max_canvas_h, new_disp_h + CANVAS_PADDING_PX)
        base_x = (new_canvas_w - new_disp_w) // 2
        base_y = (new_canvas_h - new_disp_h) // 2
        new_offset_x = event.x - old_img_x * new_display_scale
        new_offset_y = event.y - old_img_y * new_display_scale
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
