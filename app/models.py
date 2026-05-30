from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Detection:
    original_bbox: np.ndarray
    warp_bbox: Optional[np.ndarray]
    confidence: float
    category_id: int
    track_id: Optional[int]
    source: str
    internal_id: Optional[int] = None


@dataclass
class ByteTrackerArgs:
    """Arguments to initialise BYTETracker (YOLOX compatibility)."""

    track_thresh: float = 0.3
    track_buffer: int = 30
    match_thresh: float = 0.8
    aspect_ratio_thresh: float = 1.6
    min_box_area: float = 10
    mot20: bool = False
