"""Types shared across the export flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from app.annotation.core.augmentation.augmentation_types import AugmentationPreset


@dataclass
class ExportConfig:
    destination_parent: Path
    folder_name: str
    formats: List[str]
    use_split: bool
    split_ratios: Tuple[float, float, float]
    augmentation: Optional[AugmentationPreset] = None
