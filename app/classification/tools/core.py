"""Composition root for the manual image classification tool."""

from __future__ import annotations

import tkinter as tk

from PIL import Image

from app.classification.dataset import STATE_FILE_NAME, ClassificationRecord, discover_images, prepare_dataset
from app.classification.tools.class_actions import ClassificationClassActionsMixin
from app.classification.tools.dataset_actions import ClassificationDatasetActionsMixin
from app.classification.tools.navigation import ClassificationNavigationMixin
from app.classification.tools.state import ClassificationStateMixin
from app.classification.tools.ui import ClassificationUIMixin
from app.core.session import AnnotationSessionConfig
from app.ui.layout.responsive_window import apply_responsive_geometry
from app.ui.theme import install_scaled_theme


class ClassificationTool(
    ClassificationDatasetActionsMixin,
    ClassificationClassActionsMixin,
    ClassificationNavigationMixin,
    ClassificationUIMixin,
    ClassificationStateMixin,
):
    """Manual image classification UI.

    Clicking a class records the association in ``classification_state.json``
    and advances to the next pending image.
    """

    def __init__(self, *, session_config: AnnotationSessionConfig):
        self.session_config = session_config
        self.data_root = session_config.data_root
        self.output_dir = session_config.output_dir
        self.classes = list(session_config.target_classes)
        self.move_files = False
        self.state_path = session_config.annotations_path or (self.output_dir / STATE_FILE_NAME)

        self.root = tk.Tk()
        self.root.title("Classificacao de imagens")
        self.ui = install_scaled_theme(self.root)
        self.colors = self.ui["colors"]
        self.fonts = self.ui["fonts"]
        self.spacing = self.ui["spacing"]
        self.sizes = self.ui["sizes"]
        self.root.configure(bg=self.colors["bg"])
        apply_responsive_geometry(self.root, width_ratio=0.92, height_ratio=0.88)
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)

        self.images = discover_images(self.data_root)
        if not self.images:
            self.root.destroy()
            raise FileNotFoundError(f"Nenhuma imagem valida encontrada em {self.data_root}")
        self.source_image_count = len(self.images)

        self.class_directories = prepare_dataset(self.output_dir, self.classes)
        self.records: list[ClassificationRecord] = []
        self.undo_stack: list[ClassificationRecord] = []
        self.current_index = 0
        self.current_image: Image.Image | None = None
        self._photo = None
        self._render_retry_scheduled = False

        self.info_var = tk.StringVar(value="")
        self.counter_var = tk.StringVar(value="")
        self.image_name_var = tk.StringVar(value="")
        self.current_class_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.new_class_var = tk.StringVar(value="")

        self._load_existing_state()
        self._skip_classified_forward()
        self._build_ui()
        self._bind_shortcuts()
        self._load_current_image()

    def run(self):
        self.root.mainloop()

    def finish_processing(self, message: str = ""):
        if message:
            print(f"[INFO] {message}")
        self.on_quit()
