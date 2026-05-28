"""Renderizacao OpenCV de deteccoes e overlays no frame."""

from backend.annotation.shared import *


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

    def draw_detections(self, frame: np.ndarray, detections: List[Detection], source_tag: str):
        category_name_by_id = self.category_name_by_id()
        category_color_by_id = self.category_color_by_id()
        for idx, det in enumerate(detections):
            x1, y1, x2, y2 = det.original_bbox.astype(int)
            color = self.hex_to_bgr(category_color_by_id.get(det.category_id, "#22c55e"))
            thickness = 3 if self.selected_detection == (source_tag, idx) else 2
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
                label = f"[selecionada] {label}"
            cv2.putText(frame, label, (x1, max(y1 - 8, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame

    def draw_roi_overlay_on_frame(self, frame: np.ndarray) -> np.ndarray:
        if not self.roi_points:
            return frame
        pts = np.array(self.roi_points, dtype=np.int32)
        is_closed = len(self.roi_points) == 4
        cv2.polylines(frame, [pts], isClosed=is_closed, color=(255, 0, 0), thickness=2)
        for idx, (x, y) in enumerate(self.roi_points):
            xi, yi = int(round(x)), int(round(y))
            cv2.circle(frame, (xi, yi), 4, (0, 0, 255), -1)
            cv2.putText(frame, str(idx + 1), (xi + 4, yi - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        return frame
