"""Fachada de classificacao para o SessionManager."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from backend.core.session import AnnotationSessionConfig
from backend.classification.dataset import (
    STATE_FILE_NAME,
    ClassificationRecord,
    add_class_directory,
    class_directory_has_files,
    classify_image_source,
    discover_images,
    export_classification_dataset,
    prepare_dataset,
    remove_class_directory,
)
from backend.classification.tools.state import ClassificationStateMixin


class ClassificationService(ClassificationStateMixin):
    """Servico de classificacao sem UI — exposto pelo FastAPI."""

    def __init__(self, *, session_config: AnnotationSessionConfig):
        self.session_config = session_config
        self.data_root = session_config.data_root
        self.output_dir = session_config.output_dir
        self.classes = list(session_config.target_classes)
        self.state_path = session_config.annotations_path or (self.output_dir / STATE_FILE_NAME)
        self.closed = False

        self.images = discover_images(self.data_root)
        self.source_image_count = len(self.images)
        self.class_directories = prepare_dataset(self.output_dir, self.classes)
        self.records: list[ClassificationRecord] = []
        self.undo_stack: list[ClassificationRecord] = []
        self.current_index = 0

        self._load_existing_state()
        self._skip_classified_forward()

    # ── Navegação ─────────────────────────────────────────────────────────────

    def _skip_classified_forward(self):
        classified = self._classified_sources()
        while self.current_index < len(self.images) and self.images[self.current_index] in classified:
            self.current_index += 1

    def get_state_snapshot(self) -> dict:
        current_image = self.images[self.current_index] if self.current_index < len(self.images) else None
        current_record = self._record_for_source(current_image) if current_image else None
        return {
            "mode": "classification",
            "current_index": self.current_index,
            "total_images": len(self.images),
            "current_image": str(current_image) if current_image else None,
            "current_class": current_record.class_name if current_record else None,
            "classes": self.classes,
            "counts": self._counts_by_class(),
            "completed": self.current_index >= len(self.images),
        }

    def render_frame(self) -> bytes:
        """Retorna imagem atual como JPEG bytes."""
        import cv2
        from io import BytesIO
        from PIL import Image

        if self.current_index >= len(self.images):
            return b""
        path = self.images[self.current_index]
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((1200, 900))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=88)
            return buf.getvalue()
        except Exception:
            return b""

    def classify(self, class_name: str) -> None:
        if self.current_index >= len(self.images):
            return
        source_path = self.images[self.current_index]
        previous = self._record_for_source(source_path)
        record = classify_image_source(
            source_path,
            class_name=class_name,
            output_dir=self.output_dir,
            class_directories=self.class_directories,
        )
        if previous:
            self._remove_previous_classification(previous)
        self.records.append(record)
        self.undo_stack.append(record)
        self._save_state()
        self.current_index += 1
        self._skip_classified_forward()

    def skip(self) -> None:
        if self.current_index < len(self.images):
            self.current_index += 1

    def previous(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1

    def undo(self) -> None:
        if not self.undo_stack:
            return
        record = self.undo_stack.pop()
        self.records = [r for r in self.records if r != record]
        try:
            self.current_index = self.images.index(record.source_path)
        except ValueError:
            self.current_index = max(0, self.current_index - 1)
        self._save_state()

    def export(self, export_root: Path) -> dict:
        self._save_state()
        return export_classification_dataset(
            records=self.records,
            classes=self.classes,
            class_directories=self.class_directories,
            dataset_root=export_root,
        )

    def finish_processing(self, message: str = "") -> None:
        self._save_state()
        self.closed = True
        if message:
            print(f"[INFO] {message}")
