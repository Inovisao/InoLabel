"""Pure split logic for YOLO export."""

from __future__ import annotations

import math
from typing import Any, Dict, Sequence, Tuple


def normalize_split_ratios(split_ratios: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Validate and normalize split ratios so they sum to exactly 1.0."""
    if len(split_ratios) != 3:
        raise ValueError("split_ratios must contain train, val and test.")
    if any(ratio < 0 for ratio in split_ratios):
        raise ValueError("split_ratios cannot contain negative values.")
    total = sum(split_ratios)
    if total <= 0:
        raise ValueError("split_ratios must have a positive sum.")
    return tuple(ratio / total for ratio in split_ratios)


def compute_split_counts(total: int, split_ratios: Tuple[float, float, float]) -> Dict[str, int]:
    if total <= 0:
        return {"train": 0, "val": 0, "test": 0}
    if total < 3:
        return {"train": total, "val": 0, "test": 0}

    train_ratio, val_ratio, test_ratio = split_ratios
    raw_counts = {
        "train": total * train_ratio,
        "val": total * val_ratio,
        "test": total * test_ratio,
    }
    counts = {name: int(math.floor(value)) for name, value in raw_counts.items()}
    remainder = total - sum(counts.values())
    fractional = sorted(
        ((raw_counts[name] - counts[name], name) for name in ("train", "val", "test")),
        reverse=True,
    )
    for _, name in fractional[:remainder]:
        counts[name] += 1

    if counts["train"] == 0:
        donor = "val" if counts["val"] > counts["test"] else "test"
        if counts[donor] > 1:
            counts[donor] -= 1
            counts["train"] += 1
    return counts


def assign_splits(images: Sequence[Dict[str, Any]], split_ratios: Tuple[float, float, float]) -> Dict[int, str]:
    ordered_images = sorted(images, key=lambda image: str(image.get("file_name", "")))
    counts = compute_split_counts(len(ordered_images), split_ratios)
    assignments: Dict[int, str] = {}
    cursor = 0
    for split in ("train", "val", "test"):
        for image in ordered_images[cursor : cursor + counts[split]]:
            assignments[int(image.get("id"))] = split
        cursor += counts[split]
    return assignments
