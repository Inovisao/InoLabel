from app.annotation.shared import *


class TrackingIdsMixin:
    def consume_manual_id_override(self) -> Optional[int]:
        """Consumes a manual ID typed by the user (if valid)."""
        raw = self.manual_id_var.get().strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            print("[AVISO] ID manual invalido, informe um numero inteiro.")
            return None
        if value <= 0:
            print("[AVISO] ID manual deve ser > 0.")
            return None
        self.manual_id_var.set("")
        if value >= self.global_track_counter:
            self.global_track_counter = value + 1
        return value

    def new_track_id(self) -> int:
        """Generates a new sequential track_id and initialises its history."""
        tid = self.global_track_counter
        self.global_track_counter += 1
        self.track_history[tid] = []
        return tid

    def get_global_id(self, internal_id: int, category_id: Optional[int] = None) -> int:
        """Maps a ByteTrack internal ID to a fixed, sequential global ID."""
        key = (int(category_id or 0), int(internal_id))
        if key not in self.tracker_id_map:
            self.tracker_id_map[key] = self.new_track_id()
        return self.tracker_id_map[key]

    def match_manual_to_history(self, manual_bbox: np.ndarray) -> Optional[int]:
        """Matches a manual annotation by prioritising current-frame detections, then recent history."""
        cx1, cy1 = bbox_center(manual_bbox)

        # 1) highest priority: detections from the current frame
        for det in self.current_detections:
            iou = bbox_iou(manual_bbox, det.original_bbox)
            if iou > 0.4:
                return det.track_id

        # 2) fallback: previous frames
        best_id = None
        best_score = 0.0
        for frame_data in reversed(self.recent_tracks):
            for tr in frame_data.get("tracks", []):
                iou = bbox_iou(manual_bbox, tr["bbox"])
                if iou < 0.1:
                    continue
                cx2, cy2 = bbox_center(tr["bbox"])
                dist = np.hypot(cx1 - cx2, cy1 - cy2)
                combined = iou - 0.001 * dist
                if combined > best_score:
                    best_score = combined
                    best_id = tr["id"]

        if best_score > 0.2:
            return best_id

        return None

    # ===================== FLOW CONTROL =====================
