from app.annotation.shared import *


class DisplayOverlaysMixin:
    @staticmethod
    def hex_to_bgr(color: str) -> Tuple[int, int, int]:
        clean = color.strip().lstrip("#")
        if len(clean) != 6:
            return (0, 255, 0)
        try:
            r = int(clean[0:2], 16)
            g = int(clean[2:4], 16)
            b = int(clean[4:6], 16)
        except ValueError:
            return (0, 255, 0)
        return (b, g, r)

    def _draw_roi_overlay_on_canvas(self):
        if not self.roi_points:
            return
        shifted = [self.image_to_canvas_coords(x, y) for (x, y) in self.roi_points]
        if len(shifted) >= 2:
            for i in range(len(shifted) - 1):
                self.canvas.create_line(
                    shifted[i][0],
                    shifted[i][1],
                    shifted[i + 1][0],
                    shifted[i + 1][1],
                    fill="blue",
                    width=2,
                )
            if len(shifted) == 4:
                self.canvas.create_line(
                    shifted[-1][0],
                    shifted[-1][1],
                    shifted[0][0],
                    shifted[0][1],
                    fill="blue",
                    width=2,
                )
        for sx, sy in shifted:
            self.canvas.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill="red", outline="")

    def _draw_active_manual_rectangle(self):
        if self.drawing_rect_id is None or self.drawing_start is None:
            return
        x, y = self.drawing_start
        self.drawing_rect_id = self.canvas.create_rectangle(x, y, x, y, outline="yellow", width=2, dash=(4, 2))

    def draw_detections(self, frame: np.ndarray, detections: List[Detection], source_tag: str):
        category_name_by_id = self.category_name_by_id()
        category_color_by_id = self.category_color_by_id()
        for idx, det in enumerate(detections):
            x1, y1, x2, y2 = det.original_bbox.astype(int)
            color = self.hex_to_bgr(category_color_by_id.get(det.category_id, "#22c55e"))
            thickness = 2
            if self.selected_detection == (source_tag, idx):
                thickness = 3
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            class_name = str(category_name_by_id.get(det.category_id, det.category_id))
            label = class_name
            if det.track_id is not None:
                label += f" | ID {det.track_id}"
            if det.source == "model":
                label += f" {det.confidence * 100:.1f}%"
            else:
                label += " manual"
            if self.selected_detection == (source_tag, idx):
                label = f"[selected] {label}"
            cv2.putText(frame, label, (x1, max(y1 - 8, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame
