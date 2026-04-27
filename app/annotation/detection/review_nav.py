from app.annotation.shared import *


class ReviewNavMixin:
    def append_saved_record(self, detections: List[Detection], image_id: int, file_name: str):
        """Guarda frame anotado para revisao posterior."""
        if self.current_frame is None:
            return
        record = {
            "image_id": image_id,
            "file_name": file_name,
            "frame_index": self.frame_index,
            "frame": self.current_frame.copy(),
            "rectified_frame": self.current_rectified_frame.copy() if self.current_rectified_frame is not None else None,
            "detections": [self.clone_detection(det) for det in detections],
        }
        self.saved_records.append(record)
        if len(self.saved_records) > MAX_SAVED_FRAME_CACHE:
            self.saved_records.pop(0)
            if self.review_idx is not None:
                self.review_idx = max(0, self.review_idx - 1)
        self.review_idx = None
        self.live_snapshot = None

    def update_saved_record(self, idx: int, detections: List[Detection], image_id: int, file_name: str):
        """Atualiza um registro salvo apos reanotacao."""
        if idx < 0 or idx >= len(self.saved_records) or self.current_frame is None:
            return
        self.saved_records[idx] = {
            "image_id": image_id,
            "file_name": file_name,
            "frame_index": self.frame_index,
            "frame": self.current_frame.copy(),
            "rectified_frame": self.current_rectified_frame.copy() if self.current_rectified_frame is not None else None,
            "detections": [self.clone_detection(det) for det in detections],
        }

    def rebuild_detections_from_annotations(self, image_id: int, width: int, height: int) -> List[Detection]:
        """Reconstrui deteccoes a partir das anotacoes salvas."""
        dets: List[Detection] = []
        for ann in self.annotations:
            if ann.get("image_id") != image_id:
                continue
            bbox = ann.get("bbox", [0, 0, 0, 0])
            x1, y1, w, h = bbox
            x2 = x1 + w
            y2 = y1 + h
            clipped = clip_bbox(x1, y1, x2, y2, width, height)
            dets.append(
                Detection(
                    original_bbox=clipped,
                    warp_bbox=None,
                    confidence=float(ann.get("score", 1.0)),
                    category_id=int(ann.get("category_id", 1)),
                    track_id=int(ann.get("track_id", -1)),
                    source=ann.get("source", "manual"),
                    internal_id=None,
                )
            )
        return dets

    def go_to_saved_frame(self, idx: int):
        """Entra em modo revisao e carrega um frame salvo."""
        if not self.saved_records or idx < 0 or idx >= len(self.saved_records):
            print("[INFO] Nenhum frame salvo para revisar.")
            return
        if self.review_idx is None and self.current_frame is not None:
            self.live_snapshot = {
                "frame": self.current_frame.copy(),
                "rectified": self.current_rectified_frame.copy() if self.current_rectified_frame is not None else None,
                "detections": [self.clone_detection(det) for det in self.current_detections],
                "manual_detections": [self.clone_detection(det) for det in self.manual_detections],
                "frame_index": self.frame_index,
                "source_image_path": self.current_source_image_path,
            }
        record = self.saved_records[idx]
        self.review_idx = idx
        self.frame_index = record["frame_index"]
        self.current_frame = record["frame"].copy()
        self.current_source_image_path = None
        self.current_rectified_frame = self.warp_frame(self.current_frame)
        dets = self.rebuild_detections_from_annotations(
            record["image_id"], self.current_frame.shape[1], self.current_frame.shape[0]
        )
        self.current_detections = [d for d in dets if d.source == "model"]
        self.manual_detections = [d for d in dets if d.source != "model"]
        self.selected_detection = None
        self.annotation_mode = True
        self.remove_mode = False
        self.update_display()

    def on_prev_saved(self):
        """Navega para frame salvo anterior."""
        if not self.saved_records:
            print("[INFO] Nenhum frame salvo para revisar.")
            return
        if self.review_idx is None:
            self.go_to_saved_frame(len(self.saved_records) - 1)
        else:
            self.go_to_saved_frame(max(0, self.review_idx - 1))

    def on_next_saved(self):
        """Navega para proximo frame salvo; se for o ultimo, sai da revisao."""
        if not self.saved_records:
            print("[INFO] Nenhum frame salvo para revisar.")
            return
        if self.review_idx is None:
            self.go_to_saved_frame(0)
            return
        next_idx = self.review_idx + 1
        if next_idx < len(self.saved_records):
            self.go_to_saved_frame(next_idx)
        else:
            self.exit_review_mode()

    def exit_review_mode(self):
        """Retorna ao fluxo ao vivo apos revisao."""
        if self.live_snapshot is not None:
            snap = self.live_snapshot
            self.frame_index = snap["frame_index"]
            self.current_frame = snap["frame"]
            self.current_rectified_frame = snap["rectified"]
            self.current_detections = snap["detections"]
            self.manual_detections = snap["manual_detections"]
            self.current_source_image_path = snap.get("source_image_path")
            self.selected_detection = None
            self.live_snapshot = None
            self.review_idx = None
            self.update_display()
            return
        self.review_idx = None
        self.load_next_frame()

    def advance_after_review_accept(self):
        """Avanca apos aceitar revisao."""
        if self.review_idx is None:
            return
        next_idx = self.review_idx + 1
        if next_idx < len(self.saved_records):
            self.go_to_saved_frame(next_idx)
        else:
            self.exit_review_mode()

