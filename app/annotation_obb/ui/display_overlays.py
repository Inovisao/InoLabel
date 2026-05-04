from app.annotation_obb.shared import *


class OBBDisplayOverlaysMixin:
    @staticmethod
    def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
        color = hex_color.lstrip("#")
        if len(color) != 6:
            return (34, 197, 94)
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        return (b, g, r)

    def draw_obb_detections(self, frame: np.ndarray, detections: List[OBBDetection], source: str) -> np.ndarray:
        category_name_by_id = self.category_name_by_id()
        category_color_by_id = self.category_color_by_id()
        selected = self.selected_obb
        for idx, det in enumerate(detections):
            color = self.hex_to_bgr(category_color_by_id.get(det.category_id, "#22c55e"))
            if selected == (source, idx):
                color = (0, 255, 255)
            points = obb_to_points(det.cx, det.cy, det.width, det.height, det.angle).astype(np.int32)
            cv2.polylines(frame, [points], isClosed=True, color=color, thickness=2)
            for x, y in points:
                cv2.circle(frame, (int(x), int(y)), 3, color, -1)
            cx, cy = int(round(det.cx)), int(round(det.cy))
            cv2.circle(frame, (cx, cy), 4, color, -1)
            hx, hy = self.rotation_handle_image_pos(det)
            cv2.line(frame, (cx, cy), (int(round(hx)), int(round(hy))), color, 1)
            cv2.circle(frame, (int(round(hx)), int(round(hy))), 5, color, 1)
            label = category_name_by_id.get(det.category_id, str(det.category_id))
            cv2.putText(
                frame,
                f"{label} {det.angle:.0f}deg",
                (int(points[0][0]), max(15, int(points[0][1]) - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )
        return frame

    def rotation_handle_image_pos(self, det: OBBDetection) -> Tuple[float, float]:
        theta = math.radians(det.angle - 90.0)
        distance = max(24.0, det.height / 2.0 + 28.0)
        return det.cx + math.cos(theta) * distance, det.cy + math.sin(theta) * distance

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
        if self.drawing_start is None or self.drawing_rect_id is None:
            return
