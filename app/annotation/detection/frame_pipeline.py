import threading

from app.annotation.shared import *


class FramePipelineMixin:
    def process_current_frame(self, frame: np.ndarray, advance_index: bool = True, *, render: bool = True):
        if frame is None:
            return

        self.review_idx = None
        self.live_snapshot = None
        self.zoom_scale = 1.0
        self.zoom_pan_x = 0
        self.zoom_pan_y = 0
        self.frame_rotation = 0

        if advance_index:
            self.frame_index += 1
        self.current_frame = frame
        self.current_rectified_frame = self.warp_frame(frame)
        self.current_detections = []
        self.manual_detections = []
        self.selected_detection = None
        self.undo_stack = deque(maxlen=self.max_undo_states)
        self.annotation_mode = True
        self.remove_mode = False
        self.selection_mode = False
        self.pan_mode = False
        self.pan_drag_start = None
        self.drawing_start = None
        if self.drawing_rect_id is not None:
            self.canvas.delete(self.drawing_rect_id)
            self.drawing_rect_id = None
        self.update_annotation_button()
        self.update_remove_button()
        self.update_selection_button()
        if render:
            self.update_display(refresh_status=True)

        # Run model inference in background — UI stays responsive
        inference_frame = self.current_rectified_frame if self.current_rectified_frame is not None else frame
        frame_index_snapshot = self.frame_index

        def _infer():
            try:
                detections = self.run_model(frame)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[ERRO] Inferencia falhou: {exc}")
                return
            # Only apply if still on the same frame (user hasn't advanced)
            def _apply():
                if self.frame_index == frame_index_snapshot and self.review_idx is None:
                    self.current_detections = detections
                    self.update_display(refresh_status=True)
            self.window.after(0, _apply)

        threading.Thread(target=_infer, daemon=True).start()

    def load_next_frame(self):
        if self.review_idx is not None:
            return
        self.autosave_current_frame(reason="before switching frame")

        if self.current_source_type == "video":
            if self.cap is None:
                self.finish_current_video()
                return
            ret, frame = self.cap.read()
            if not ret:
                self.finish_current_video()
                return
            self.current_source_image_path = None
        else:
            frame = self.read_next_image_frame()
            if frame is None:
                self.finish_current_video()
                return

        self.process_current_frame(frame, render=False)
        self.restore_saved_annotations_for_current_frame()
        self.update_display(refresh_status=True)

    def run_model(self, original_frame: np.ndarray) -> List[Detection]:
        detections: List[Detection] = []
        if original_frame is None:
            return detections

        img_height, img_width = original_frame.shape[:2]
        dets, scores, det_category_ids = self._extract_model_candidates(original_frame, img_width, img_height)
        img_dims = (img_height, img_width)

        if not self.tracking_enabled:
            total_dets = len(dets)
            roi_filtered = 0
            for box, score, category_id in zip(dets, scores, det_category_ids):
                original_box = clip_bbox(box[0], box[1], box[2], box[3], img_width, img_height)
                if not self.is_inside_roi(original_box):
                    roi_filtered += 1
                    continue
                warp_box = None
                if self.homography_matrix is not None and self.warp_size is not None:
                    warp_box = self.project_bbox(
                        original_box, self.homography_matrix, self.warp_size[0], self.warp_size[1]
                    )
                detections.append(
                    Detection(
                        original_bbox=original_box,
                        warp_bbox=warp_box,
                        confidence=float(score),
                        category_id=int(category_id),
                        track_id=None,
                        source="model",
                        internal_id=None,
                    )
                )
            if total_dets > 0:
                print(f"[DETECÇÃO] Frame {self.frame_index}: {total_dets} detections → {len(detections)} após ROI (filtradas: {roi_filtered})")
            return detections

        if not dets:
            self.multiclass_tracker.update([], [], [], img_dims, img_dims)
            return detections

        total_dets = len(dets)
        tracks = self.multiclass_tracker.update(dets, scores, det_category_ids, img_dims, img_dims)

        for category_id, track in tracks:
            tlbr = track.tlbr
            internal_id = int(track.track_id)
            track_id = self.get_global_id(internal_id, category_id)
            score = float(track.score)
            original_box = clip_bbox(tlbr[0], tlbr[1], tlbr[2], tlbr[3], img_width, img_height)
            if not self.is_inside_roi(original_box):
                continue
            warp_box = None
            if self.homography_matrix is not None and self.warp_size is not None:
                warp_box = self.project_bbox(original_box, self.homography_matrix, self.warp_size[0], self.warp_size[1])
            self.track_history.setdefault(track_id, []).append({"frame": self.frame_index, "bbox": original_box.tolist()})
            detections.append(
                Detection(
                    original_bbox=original_box,
                    warp_bbox=warp_box,
                    confidence=score,
                    category_id=int(category_id),
                    track_id=track_id,
                    source="model",
                    internal_id=internal_id,
                )
            )

        frame_tracks = [{"id": det.track_id, "bbox": det.original_bbox.copy()} for det in detections]
        self.recent_tracks.append({"frame": self.frame_index, "tracks": frame_tracks})

        roi_filtered_tracking = total_dets - len(tracks)
        detected_tracks = len(detections)
        print(f"[TRACKING] Frame {self.frame_index}: {total_dets} detections → {len(tracks)} tracks → {detected_tracks} após ROI (fragmentadas: {roi_filtered_tracking})")

        if detected_tracks < len(tracks) * 0.3:
            print(f"[AVISO] Possível fragmentação de tracks detectada no frame {self.frame_index}")

        return detections
