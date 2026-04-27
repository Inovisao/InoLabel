from app.annotation.shared import *


class CoreInitMixin:
    def __init__(self):
        self._validate_required_paths()
        self.video_files = self.discover_sources(DATA_ROOT)
        if not self.video_files:
            raise FileNotFoundError(f"Nenhuma fonte valida encontrada em {DATA_ROOT}")

        OUTPUT_DIR.mkdir(exist_ok=True)
        OUTPUT_IMAGES_DIR.mkdir(exist_ok=True)

        self._initialize_model_state()
        self._initialize_runtime_state()
        self._build_ui()
        self.load_existing_annotations()
        self.register_signal_handlers()
        self.start_video(self.current_video_index)

    def _validate_required_paths(self):
        if not DATA_ROOT.exists():
            raise FileNotFoundError(f"Origem de dados nao encontrada: {DATA_ROOT}")
        if not WEIGHTS_PATH.exists():
            raise FileNotFoundError(f"Pesos nao encontrados: {WEIGHTS_PATH}")

    def _initialize_model_state(self):
        self.model = YOLO(str(WEIGHTS_PATH))
        self.target_classes = [name.strip() for name in TARGET_CLASSES if name.strip()]
        self.class_to_category_id: Dict[str, int] = {}
        self.categories: List[dict] = []
        for cname in self.target_classes:
            self.register_category(cname)
        self.uses_text_prompt = False
        self.apply_target_classes(self.target_classes)

