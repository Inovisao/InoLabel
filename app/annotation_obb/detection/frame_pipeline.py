from app.annotation_obb.shared import *


class OBBFramePipelineMixin:
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
        self.current_obb_detections = self.run_model(frame)
        self.manual_obb_detections = []
        self.current_detections = self.current_obb_detections
        self.manual_detections = self.manual_obb_detections
        self.selected_obb = None
        self.selected_detection = None
        self.undo_stack = deque(maxlen=self.max_undo_states)
        self.annotation_mode = True
        self.remove_mode = False
        self.selection_mode = False
        self.pan_mode = False
        self.obb_interaction_mode = None
        self.drag_start = None
        self.drawing_start = None
        if self.drawing_rect_id is not None:
            self.canvas.delete(self.drawing_rect_id)
            self.drawing_rect_id = None
        self.update_annotation_button()
        self.update_remove_button()
        self.update_selection_button()
        if render:
            self.update_display(refresh_status=True)

    def load_next_frame(self):
        if self.review_idx is not None:
            return
        self.autosave_current_frame(reason="antes de trocar frame")

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

    def run_model(self, original_frame: np.ndarray) -> List[OBBDetection]:
        if original_frame is None:
            return []
        img_height, img_width = original_frame.shape[:2]
        detections = self._extract_model_obb_candidates(original_frame, img_width, img_height)
        kept = []
        for det in detections:
            points = obb_to_points(det.cx, det.cy, det.width, det.height, det.angle)
            x, y, w, h = points_to_hbb(points)
            if not self.is_inside_roi(np.array([x, y, x + w, y + h], dtype=np.float32)):
                continue
            kept.append(clip_obb_to_image(det, img_width, img_height))
        return kept
