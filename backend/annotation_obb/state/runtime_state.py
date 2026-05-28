from backend.annotation_obb.shared import *


class _NoopTracker:
    def reset(self):
        return None


class OBBRuntimeStateMixin:
    def _initialize_runtime_state(self):
        self.default_tracker_args = ByteTrackerArgs()
        self.frame_rate = 30
        self.bytetracker = _NoopTracker()
        self.multiclass_tracker = _NoopTracker()

        self.cap = None
        self.current_source_type = "video"
        self.current_image_paths: List[Path] = []
        self.current_image_cursor = 0
        self.current_source_image_path: Optional[Path] = None
        self.video_name = ""
        self.video_path: Optional[Path] = None
        self.current_video_index = 0
        self.frame_index = 0
        self.image_id = 1
        self.annotation_id = 1
        self.frames_saved_in_current_video = 0

        self.current_frame: Optional[np.ndarray] = None
        self.current_rectified_frame: Optional[np.ndarray] = None
        self.last_frame_shape: Optional[Tuple[int, int]] = None
        self.offset_x = 0
        self.offset_y = 0
        self.display_scale = 1.0
        self.zoom_scale = 1.0
        self.zoom_pan_x = 0
        self.zoom_pan_y = 0
        self.pan_mode = False
        self.pan_drag_start: Optional[Tuple[int, int]] = None
        self.pan_start_offset: Tuple[int, int] = (0, 0)
        self.key_mapping_mode = "arrows"
        self.frame_rotation: int = 0  # 0 / 90 / 180 / 270 — visual only

        self.roi_points: List[Tuple[int, int]] = []
        self.roi_defined = False
        self.roi_capture_mode = False
        self.homography_matrix: Optional[np.ndarray] = None
        self.inverse_homography: Optional[np.ndarray] = None
        self.warp_size: Optional[Tuple[int, int]] = None
        self.roi_polygon: Optional[np.ndarray] = None
        self.dest_points: Optional[np.ndarray] = None

        self.images: List[dict] = []
        self.annotations: List[dict] = []
        self.annotation_state: dict = {}
        self.homographies: List[dict] = []

        self.max_undo_states = 40
        self.undo_stack: deque = deque(maxlen=self.max_undo_states)

        self.current_obb_detections: List[OBBDetection] = []
        self.manual_obb_detections: List[OBBDetection] = []
        # Compatibility for reused class/status widgets.
        self.current_detections = self.current_obb_detections
        self.manual_detections = self.manual_obb_detections

        self.annotation_mode = True
        self.remove_mode = False
        self.selection_mode = False
        self.edit_id_mode = False
        self.obb_interaction_mode = None
        self.selected_obb: Optional[Tuple[str, int]] = None
        self.selected_detection = None
        self.drag_start: Optional[Tuple[int, int]] = None
        self.rotate_start_angle: Optional[float] = None
        self.drawing_start: Optional[Tuple[int, int]] = None
        self.drawing_rect_id: Optional[int] = None

        self.manual_track_memory: Dict[int, Dict[str, np.ndarray]] = {}
        self.global_track_counter = 1
        self.track_history: Dict[int, List[dict]] = {}
        self.history_window = 5
        self.recent_tracks: deque = deque(maxlen=self.history_window)
        self.tracker_id_map: Dict[Tuple[int, int], int] = {}

        self.saved_records: List[dict] = []
        self.review_idx: Optional[int] = None
        self.live_snapshot: Optional[dict] = None
        self.closed = False
