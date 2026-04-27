"""ByteTrack wrapper that keeps independent trackers per class."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import numpy as np

from app.models import ByteTrackerArgs
from tracker.byte_tracker import BYTETracker


class MultiClassByteTracker:
    """Run one BYTETracker per category to avoid cross-class identity switches."""

    def __init__(self, args: ByteTrackerArgs, frame_rate: int):
        self.args = args
        self.frame_rate = frame_rate
        self._trackers: Dict[int, BYTETracker] = {}

    def reset(self):
        self._trackers.clear()

    def update(
        self,
        boxes: Iterable[np.ndarray],
        scores: Iterable[float],
        category_ids: Iterable[int],
        img_info: Tuple[int, int],
        img_size: Tuple[int, int],
    ) -> List[Tuple[int, object]]:
        grouped: Dict[int, List[Tuple[np.ndarray, float]]] = {}
        for box, score, category_id in zip(boxes, scores, category_ids):
            grouped.setdefault(int(category_id), []).append((np.asarray(box, dtype=np.float32), float(score)))

        results: List[Tuple[int, object]] = []
        for category_id, items in grouped.items():
            tracker = self._trackers.setdefault(category_id, BYTETracker(self.args, frame_rate=self.frame_rate))
            detections = np.concatenate(
                [
                    np.array([item[0] for item in items], dtype=np.float32),
                    np.array([item[1] for item in items], dtype=np.float32).reshape(-1, 1),
                ],
                axis=1,
            )
            for track in tracker.update(detections, img_info, img_size):
                results.append((category_id, track))

        empty = np.empty((0, 5), dtype=np.float32)
        for category_id, tracker in list(self._trackers.items()):
            if category_id not in grouped:
                tracker.update(empty, img_info, img_size)
        return results

