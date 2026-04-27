from app.annotation.shared import *


class MouseEventsMixin:
    def on_mouse_down(self, event):
        if self.current_frame is None:
            return

        img_coords = self.canvas_to_image_coords(event.x, event.y)
        if img_coords is None:
            return
        x, y = img_coords

        if self.roi_capture_mode and not self.roi_defined:
            self.add_roi_point(x, y)
            return
        if self.edit_id_mode:
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

        track_id = self.consume_manual_id_override()
        if track_id is None:
            track_id = self.match_manual_to_history(bbox)
        if track_id is None:
            track_id = self.new_track_id()

        warp_bbox = None
        if self.homography_matrix is not None and self.warp_size is not None:
            warp_bbox = self.project_bbox(bbox, self.homography_matrix, self.warp_size[0], self.warp_size[1])

        manual_class_name = self.manual_class_var.get().strip() if self.manual_class_var is not None else ""
        if not manual_class_name:
            manual_class_name = self.target_classes[0] if self.target_classes else "object"
        manual_category_id = self.register_category(manual_class_name)

        manual_det = Detection(
            original_bbox=bbox,
            warp_bbox=warp_bbox,
            confidence=1.0,
            category_id=manual_category_id,
            track_id=track_id,
            source="manual",
        )
        self.manual_detections.append(manual_det)
        self.track_history.setdefault(track_id, []).append({"frame": self.frame_index, "bbox": bbox.tolist()})
        self.recent_tracks.append({"frame": self.frame_index, "tracks": [{"id": track_id, "bbox": bbox.copy()}]})
        if len(self.recent_tracks) > self.history_window:
            self.recent_tracks.pop(0)
        self.update_display()

    def remove_annotation_at(self, x: int, y: int) -> bool:
        for idx in range(len(self.manual_detections) - 1, -1, -1):
            det = self.manual_detections[idx]
            x1, y1, x2, y2 = det.original_bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                del self.manual_detections[idx]
                self.selected_detection = None
                print("[INFO] Caixa manual removida.")
                self.update_display()
                return True

        for idx in range(len(self.current_detections) - 1, -1, -1):
            det = self.current_detections[idx]
            x1, y1, x2, y2 = det.original_bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                del self.current_detections[idx]
                self.selected_detection = None
                print("[INFO] Deteccao removida.")
                self.update_display()
                return True

        print("[INFO] Nenhuma caixa encontrada para remover.")
        return False
