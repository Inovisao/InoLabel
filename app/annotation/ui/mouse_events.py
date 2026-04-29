from app.annotation.shared import *


class MouseEventsMixin:
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
        if self.edit_id_mode or self.selection_mode:
            self.select_detection_at(x, y)
            return
        if self.remove_mode:
            self.remove_annotation_at(x, y)
            return
        if not self.annotation_mode:
            return

        self.drawing_start = (x, y)
        self.drawing_rect_id = self.canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="yellow",
            width=2,
            dash=(4, 2),
        )

    def on_mouse_drag(self, event):
        if self.pan_mode:
            self.on_pan_drag(event)
            return "break"
        if self.remove_mode or not self.annotation_mode or self.drawing_start is None:
            return

        start_cx, start_cy = self.image_to_canvas_coords(self.drawing_start[0], self.drawing_start[1])
        if self.drawing_rect_id is None:
            self.drawing_rect_id = self.canvas.create_rectangle(
                start_cx,
                start_cy,
                event.x,
                event.y,
                outline="yellow",
                width=2,
                dash=(4, 2),
            )
        self.canvas.coords(self.drawing_rect_id, start_cx, start_cy, event.x, event.y)

    def on_mouse_up(self, event):
        if self.pan_mode:
            self.on_pan_end(event)
            return "break"
        if self.remove_mode or not self.annotation_mode or self.drawing_start is None:
            return

        start_x, start_y = self.drawing_start
        end_coords = self.canvas_to_image_coords(event.x, event.y)
        if end_coords is None:
            frame_h, frame_w = self.current_frame.shape[:2]
            end_x = int(np.clip((event.x - self.offset_x) / max(self.display_scale, 1e-9), 0, frame_w - 1))
            end_y = int(np.clip((event.y - self.offset_y) / max(self.display_scale, 1e-9), 0, frame_h - 1))
        else:
            end_x, end_y = end_coords

        if self.drawing_rect_id is not None:
            self.canvas.delete(self.drawing_rect_id)
            self.drawing_rect_id = None
        self.drawing_start = None

        x1, x2 = sorted((start_x, end_x))
        y1, y2 = sorted((start_y, end_y))
        if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
            return

        bbox = np.array([int(x1), int(y1), int(x2), int(y2)], dtype=np.float32)
        if not self.is_inside_roi(bbox):
            print("[INFO] Caixa manual ignorada pois esta fora do ROI.")
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

    def remove_annotation_at(self, x: int, y: int) -> bool:
        for idx in range(len(self.manual_detections) - 1, -1, -1):
            det = self.manual_detections[idx]
            x1, y1, x2, y2 = det.original_bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.push_undo_state("remover anotacao manual")
                self.remove_detection_from_runtime_state(det)
                del self.manual_detections[idx]
                self.selected_detection = None
                print("[INFO] Caixa manual removida.")
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
                print("[INFO] Deteccao removida.")
                self.update_display(refresh_status=True)
                return True

        print("[INFO] Nenhuma caixa encontrada para remover.")
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
        self.update_canvas_cursor()
        self.info_var.set("Pan ON: arraste a imagem para mover." if self.pan_mode else "Pan OFF.")
        self.update_status()

    def on_zoom(self, event):
        """Ctrl+Scroll: zoom centrado na posição do cursor."""
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

        # Ponto da imagem sob o cursor antes do zoom
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

        # Após o zoom o mesmo ponto da imagem deve estar sob o cursor:
        # event.x = old_img_x * new_display_scale + new_offset_x
        new_offset_x = event.x - old_img_x * new_display_scale
        new_offset_y = event.y - old_img_y * new_display_scale

        self.zoom_scale = new_zoom
        self.zoom_pan_x = int(round(new_offset_x - base_x))
        self.zoom_pan_y = int(round(new_offset_y - base_y))
        self.clamp_zoom_pan(new_disp_w, new_disp_h, new_canvas_w, new_canvas_h, base_x, base_y)
        self.update_display()

    def reset_zoom(self):
        """Reseta o zoom para o ajuste automático (Ctrl+0)."""
        self.zoom_scale = 1.0
        self.zoom_pan_x = 0
        self.zoom_pan_y = 0
        self.update_display()
