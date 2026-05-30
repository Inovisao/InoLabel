from app.annotation.shared import *


class ReviewCacheMixin:
    def append_saved_record(self, detections: List[Detection], image_id: int, file_name: str):
        """Stores an annotated frame in the review cache."""
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
        """Updates a cached record after re-annotation."""
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

    def remember_saved_record(self, detections: List[Detection], image_id: int, file_name: str):
        """Inserts or updates the review cache for a saved frame."""
        if self.current_frame is None:
            return
        for idx, record in enumerate(self.saved_records):
            if record.get("image_id") == image_id or record.get("file_name") == file_name:
                self.update_saved_record(idx, detections, image_id, file_name)
                return
        self.append_saved_record(detections, image_id, file_name)

    def _populate_saved_records_from_state(self):
        """Rebuilds saved_records from persisted images when resuming a previous session."""
        for img in self.images:
            file_name = str(img.get("file_name", "")).strip()
            if not file_name:
                continue
            self.saved_records.append({
                "image_id": int(img.get("id", 0)),
                "file_name": file_name,
                "frame_index": 0,
                "frame": None,  # loaded lazily on first access
                "rectified_frame": None,
                "detections": [],
            })

    def _load_record_frame(self, record: dict) -> Optional[np.ndarray]:
        """Returns the frame for a record, loading it from disk if not yet cached."""
        if record.get("frame") is not None:
            return record["frame"]
        file_name = record.get("file_name", "")
        if not file_name:
            return None
        frame = cv2.imread(str(self.output_images_dir / file_name))
        if frame is None:
            print(f"[WARN] Could not load frame from disk: {self.output_images_dir / file_name}")
            return None
        record["frame"] = frame
        return frame
