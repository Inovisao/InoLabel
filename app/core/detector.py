"""Lazy detector wrapper for API and future UI reuse."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.model_runtime import ModelRuntimeError, import_error_message


class Detector:
    """Load YOLO only when a session explicitly needs inference."""

    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path).expanduser()
        self._model: Any | None = None

    def load(self) -> Any:
        """Return a loaded YOLO model, importing ultralytics lazily."""
        if self._model is None:
            # Coexistence: never import ultralytics at FastAPI startup; Windows
            # multiprocessing stays isolated to the background session path.
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise ModelRuntimeError(import_error_message(exc)) from exc

            self._model = YOLO(str(self.model_path))
        return self._model

    def predict(self, *args, **kwargs):
        return self.load().predict(*args, **kwargs)
