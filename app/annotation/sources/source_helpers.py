from app.annotation.shared import *


class SourceHelpersMixin:
    def _reset_open_source(self):
        if self.cap is not None:
            self.cap.release()

    def _reset_model_tracking_state(self):
        if hasattr(self.model, "reset"):
            try:
                self.model.reset()
            except Exception:  # pylint: disable=broad-except
                pass
            return
        if hasattr(self.model, "tracker"):
            try:
                self.model.tracker = None
            except Exception:  # pylint: disable=broad-except
                pass

    def _prepare_source_state(self, index: int):
        self.video_path = self.video_files[index]
        self.video_name = self.video_path.stem
        self.current_video_index = index
        self.frame_index = self._find_last_saved_frame()
        self.frames_saved_in_current_video = self.frame_index

        self.manual_track_memory.clear()
        self.saved_records.clear()
        self.review_idx = None
        self.live_snapshot = None
        self.recent_tracks.clear()
        self.tracker_id_map.clear()
        self.edit_id_mode = False
        self.selected_detection = None

    def _find_last_saved_frame(self) -> int:
        if self.video_path is None:
            return 0
        last_frame_saved = 0
        saved_for_video = [img for img in self.images if img.get("video") in (str(self.video_path), self.video_name)]
        for img in saved_for_video:
            parsed = parse_frame_number_from_name(img.get("file_name", ""), self.video_name)
            if parsed is not None:
                last_frame_saved = max(last_frame_saved, parsed)
        return last_frame_saved

    def _reset_source_runtime_data(self):
        self.roi_points = []
        self.roi_defined = False
        self.roi_capture_mode = False
        self.homography_matrix = None
        self.inverse_homography = None
        self.warp_size = None
        self.roi_polygon = None
        self.dest_points = None
        self.current_rectified_frame = None
        self.current_detections = []
        self.manual_detections = []
        self.selected_detection = None

    def _load_first_frame_for_source(self) -> Optional[np.ndarray]:
        if self.video_path is None:
            return None
        if self.is_video_source(self.video_path):
            return self._load_first_frame_from_video()
        return self._load_first_frame_from_images()

    def _load_first_frame_from_video(self) -> Optional[np.ndarray]:
        if self.video_path is None:
            return None
        self.current_source_type = "video"
        self.current_image_paths = []
        self.current_image_cursor = 0
        self.current_source_image_path = None
        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            print(f"[ERRO] Falha ao abrir video: {self.video_path}")
            return None
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_rate = int(fps) if fps and fps > 1 else 30
        self.bytetracker = BYTETracker(ByteTrackerArgs(), frame_rate=self.frame_rate)
        if self.frame_index > 0:
            try:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, float(self.frame_index))
            except Exception:  # pylint: disable=broad-except
                pass
        ret, first_frame = self.cap.read()
        if not ret or first_frame is None:
            print(f"[ERRO] Falha ao ler o primeiro frame: {self.video_path}")
            return None
        return first_frame

    def _load_first_frame_from_images(self) -> Optional[np.ndarray]:
        if self.video_path is None:
            return None
        self.current_source_type = "images"
        self.cap = None
        self.current_image_paths = self.build_image_sequence(self.video_path)
        self.current_image_cursor = self.frame_index
        self.frame_rate = 30
        self.bytetracker = BYTETracker(ByteTrackerArgs(), frame_rate=self.frame_rate)
        if not self.current_image_paths:
            print(f"[ERRO] Nenhuma imagem valida encontrada para: {self.video_path}")
            return None
        first_frame = self.read_next_image_frame()
        if first_frame is None:
            print(f"[ERRO] Falha ao ler imagens da fonte: {self.video_path}")
            return None
        return first_frame

