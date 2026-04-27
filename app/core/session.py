"""Session configuration shared by startup screens and annotation runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Tuple

from app.config import CONF_THRESHOLD, OUTPUT_DIR


class AnnotationTaskMode(str, Enum):
    """Supported annotation workflows."""

    TRACKING = "tracking"
    DETECTION = "detection"

    @property
    def label(self) -> str:
        if self is AnnotationTaskMode.TRACKING:
            return "Tracking"
        return "Deteccao padrao"


@dataclass(frozen=True)
class AnnotationSessionConfig:
    """Immutable configuration chosen before the annotation UI starts."""

    mode: AnnotationTaskMode
    data_root: Path
    weights_path: Path
    target_classes: Tuple[str, ...]
    output_dir: Path = OUTPUT_DIR
    confidence_threshold: float = CONF_THRESHOLD

    def __post_init__(self):
        object.__setattr__(self, "data_root", Path(self.data_root).expanduser())
        object.__setattr__(self, "weights_path", Path(self.weights_path).expanduser())
        object.__setattr__(self, "output_dir", Path(self.output_dir).expanduser())
        object.__setattr__(self, "target_classes", normalize_class_names(self.target_classes))
        if not self.target_classes:
            raise ValueError("Informe ao menos uma classe.")
        if self.confidence_threshold < 0 or self.confidence_threshold > 1:
            raise ValueError("confidence_threshold deve ficar entre 0 e 1.")

    @property
    def tracking_enabled(self) -> bool:
        return self.mode is AnnotationTaskMode.TRACKING


def normalize_class_names(values: Iterable[str]) -> Tuple[str, ...]:
    """Return clean class names preserving order and removing duplicates."""

    cleaned = []
    seen = set()
    for value in values:
        name = str(value).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return tuple(cleaned)

