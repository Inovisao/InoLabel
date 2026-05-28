"""Fachada compatível para exportação de datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from backend.annotation.infrastructure.export.coco_exporter import (
    convert_tracking_to_detection,
    export_detection_coco_json,
    normalize_categories,
)
from backend.annotation.infrastructure.export.yolo_exporter import (
    export_yolo_dataset,
    export_yolo_no_split,
)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
