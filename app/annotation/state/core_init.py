from app.annotation.shared import *


class CoreInitMixin:
    def __init__(
        self,
        *,
        session_config: Optional[AnnotationSessionConfig] = None,
        data_root: Path = DATA_ROOT,
        weights_path: Path = WEIGHTS_PATH,
        initial_classes=None,
    ):
        if session_config is None:
            raw_classes = initial_classes if initial_classes is not None else TARGET_CLASSES
            session_config = AnnotationSessionConfig(
                mode=AnnotationTaskMode.TRACKING,
                data_root=Path(data_root),
                weights_path=Path(weights_path),
                target_classes=tuple(str(name) for name in raw_classes),
            )

        self.session_config = session_config
        self.task_mode = session_config.mode
        self.tracking_enabled = session_config.tracking_enabled
        self.data_root = session_config.data_root
        self.weights_path = session_config.weights_path
        self.output_dir = session_config.output_dir
        self.output_images_dir = self.output_dir / "images"
        self.annotations_path = self.output_dir / "annotations.coco.json"
        self.coco_detection_export_path = self.output_dir / "annotations_detection.coco.json"
        self.yolo_dataset_dir = self.output_dir / "yolo_dataset"
        self.homography_path = self.output_dir / "homography.json"
        self.conf_threshold = session_config.confidence_threshold
        self._initial_classes = list(session_config.target_classes)

        self._validate_required_paths()
        self.video_files = self.discover_sources(self.data_root)
        if not self.video_files:
            raise FileNotFoundError(f"Nenhuma fonte valida encontrada em {self.data_root}")

        self.output_dir.mkdir(exist_ok=True)
        self.output_images_dir.mkdir(exist_ok=True)

        self._initialize_model_state()
        self._initialize_runtime_state()
        self._build_ui()
        self.load_existing_annotations()
        self.register_signal_handlers()
        self.start_video(self.current_video_index)

    def _validate_required_paths(self):
        if not self.data_root.exists():
            raise FileNotFoundError(f"Origem de dados nao encontrada: {self.data_root}")

    def _initialize_model_state(self):
        self.model = None
        self.target_classes = [str(name).strip() for name in self._initial_classes if str(name).strip()]
        self.class_to_category_id: Dict[str, int] = {}
        self.categories: List[dict] = []
        for cname in self.target_classes:
            self.register_category(cname)
        self.uses_text_prompt = False
        self.apply_target_classes(self.target_classes)

    def ensure_model_loaded(self):
        if self.model is not None:
            return self.model
        if not self.weights_path.exists():
            raise FileNotFoundError(f"Pesos nao encontrados: {self.weights_path}")
        self.model = YOLO(str(self.weights_path))
        self.apply_target_classes(self.target_classes)
        return self.model
