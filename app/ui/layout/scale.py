"""UI scaling helpers for legacy Tkinter screens."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


MIN_SCALE = 1.0
MAX_SCALE = 1.35
BASE_HEIGHT = 1080
MAX_HEIGHT = 2160
BASE_DPI = 96.0
MAX_DPI = 192.0


def _clamp(value: float, low: float = MIN_SCALE, high: float = MAX_SCALE) -> float:
    return max(low, min(high, value))


def compute_ui_scale(screen_height: int, dpi: float) -> float:
    """Return a bounded scale factor from screen height and DPI."""
    height_progress = max(0.0, (float(screen_height) - BASE_HEIGHT) / (MAX_HEIGHT - BASE_HEIGHT))
    dpi_progress = max(0.0, (float(dpi) - BASE_DPI) / (MAX_DPI - BASE_DPI))
    return round(_clamp(MIN_SCALE + (height_progress * 0.25) + (dpi_progress * 0.10)), 2)


def apply_scale(tokens: dict[str, Any], scale: float) -> dict[str, Any]:
    """Scale font sizes, spacing, and fixed sizes in a token dictionary."""
    scaled = deepcopy(tokens)

    for name, font in scaled.get("fonts", {}).items():
        if isinstance(font, tuple) and len(font) >= 2 and isinstance(font[1], int):
            scaled["fonts"][name] = (font[0], round(font[1] * scale), *font[2:])

    for group in ("spacing", "sizes"):
        for key, value in scaled.get(group, {}).items():
            if isinstance(value, int):
                scaled[group][key] = round(value * scale)

    return scaled
