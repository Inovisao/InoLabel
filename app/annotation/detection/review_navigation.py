from app.annotation.shared import *


class ReviewNavigationMixin:
    def go_to_saved_frame(self, idx: int):
        """Enters review mode and loads the saved frame at the given index."""
        if not self.saved_records or idx < 0 or idx >= len(self.saved_records):
            print("[INFO] No saved frames to review.")
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
        frame = self._load_record_frame(record)
        if frame is None:
            print(f"[WARN] Frame unavailable for record {idx}, skipping.")
            return
        self.review_idx = idx
        self.frame_index = record["frame_index"]
        self.current_frame = frame.copy()
        self.current_source_image_path = None
        self.current_rectified_frame = self.warp_frame(self.current_frame)
        dets = self.rebuild_detections_from_annotations(
            record["image_id"], self.current_frame.shape[1], self.current_frame.shape[0]
        )
        self.current_detections = [d for d in dets if d.source == "model"]
        self.manual_detections = [d for d in dets if d.source != "model"]
        self.selected_detection = None
        self.undo_stack = []
        self.annotation_mode = True
        self.remove_mode = False
        self.selection_mode = False
        self.update_display(refresh_status=True)

    def on_prev_saved(self):
        """Navigates to the previous saved frame (or wraps around when all sources are done)."""
        self.autosave_current_frame(reason="before going back")
        all_done = getattr(self, "_all_sources_done", False)
        if not self.saved_records:
            if not all_done:
                self.load_previous_frame()
            return
        if self.review_idx is None:
            target = len(self.saved_records) - 1 if all_done else None
        elif self.review_idx == 0 and all_done:
            target = len(self.saved_records) - 1
        else:
            target = max(0, self.review_idx - 1)

        if target is not None:
            self.go_to_saved_frame(target)
        else:
            self.load_previous_frame()

    def on_next_saved(self):
        """Navigates to the next saved frame (or wraps around when all sources are done)."""
        self.autosave_current_frame(reason="before advancing")
        all_done = getattr(self, "_all_sources_done", False)
        if not self.saved_records:
            if not all_done:
                self.load_next_frame()
            return
        if self.review_idx is None:
            if all_done:
                self.go_to_saved_frame(0)
            else:
                self.load_next_frame()
            return
        next_idx = self.review_idx + 1
        if next_idx < len(self.saved_records):
            self.go_to_saved_frame(next_idx)
        elif all_done:
            self.go_to_saved_frame(0)
        else:
            self.exit_review_mode()

    def exit_review_mode(self):
        """Returns to the live annotation flow after review."""
        if self.live_snapshot is not None:
            snap = self.live_snapshot
            self.frame_index = snap["frame_index"]
            self.current_frame = snap["frame"]
            self.current_rectified_frame = snap["rectified"]
            self.current_detections = snap["detections"]
            self.manual_detections = snap["manual_detections"]
            self.current_source_image_path = snap.get("source_image_path")
            self.selected_detection = None
            self.undo_stack = []
            self.live_snapshot = None
            self.review_idx = None
            self.update_display(refresh_status=True)
            return
        self.review_idx = None
        self.load_next_frame()

    def advance_after_review_accept(self):
        """Advances to the next saved frame after accepting during review."""
        if self.review_idx is None:
            return
        next_idx = self.review_idx + 1
        if next_idx < len(self.saved_records):
            self.go_to_saved_frame(next_idx)
        else:
            self.exit_review_mode()

    def load_previous_frame(self):
        """Goes back one frame when the source supports repositioning."""
        if self.review_idx is not None:
            return
        if self.current_source_type == "images":
            target_cursor = max(0, self.current_image_cursor - 2)
            if target_cursor == self.current_image_cursor:
                print("[INFO] Already at the first image.")
                return
            self.current_image_cursor = target_cursor
            self.frame_index = target_cursor
            frame = self.read_next_image_frame()
            if frame is None:
                print("[INFO] Could not go back to the previous image.")
                return
            self.process_current_frame(frame, advance_index=True, render=False)
            self.restore_saved_annotations_for_current_frame()
            self.update_display(refresh_status=True)
            return

        if self.current_source_type == "video" and self.cap is not None:
            target_frame = max(0, self.frame_index - 2)
            if target_frame == self.frame_index:
                print("[INFO] Already at the first frame.")
                return
            try:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, float(target_frame))
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[WARN] Could not seek video: {exc}")
                return
            self.frame_index = target_frame
            ret, frame = self.cap.read()
            if not ret or frame is None:
                print("[INFO] Could not go back to the previous frame.")
                return
            self.current_source_image_path = None
            self.process_current_frame(frame, advance_index=True, render=False)
            self.restore_saved_annotations_for_current_frame()
            self.update_display(refresh_status=True)
            return

        print("[INFO] Current source does not support going back.")
