"""UI scale factor derived from monitor height and DPI.

Baseline: 1080p at 96 DPI → scale 1.0.
Range clamped to [1.0, 1.35].
"""

from __future__ import annotations

from copy import deepcopy

_MIN = 1.0
_MAX = 1.35
_BASE_H = 1080
_BASE_DPI = 96.0


def compute_ui_scale(screen_h: int, dpi: float) -> float:
    """Return a scale factor in [1.0, 1.35] for the given screen dimensions."""
    h_factor = screen_h / _BASE_H
    d_factor = dpi / _BASE_DPI
    raw = (h_factor + d_factor) / 2
    return max(_MIN, min(_MAX, raw))


def get_screen_dpi(root) -> float:
    """Read physical DPI from a Tk root window; falls back to 96."""
    try:
        return float(root.winfo_fpixels("1i"))
    except Exception:  # pylint: disable=broad-except
        return _BASE_DPI


def scale_int(value: int, scale: float, *, minimum: int = 1) -> int:
    """Scale an integer design token and keep it usable for Tk options."""

    return max(minimum, int(round(value * scale)))


def scale_font(font: tuple, scale: float) -> tuple:
    """Scale a Tk font tuple preserving family and style."""

    if len(font) < 2:
        return font
    family = font[0]
    size = scale_int(abs(int(font[1])), scale, minimum=8)
    if int(font[1]) < 0:
        size = -size
    return (family, size, *font[2:])


def apply_scale(tokens: dict, scale: float) -> dict:
    """Return scaled copies of FONTS, SPACING, and SIZES token dictionaries."""

    scaled = deepcopy(tokens)
    if "fonts" in scaled:
        scaled["fonts"] = {key: scale_font(value, scale) for key, value in scaled["fonts"].items()}
    if "spacing" in scaled:
        scaled["spacing"] = {key: scale_int(value, scale) for key, value in scaled["spacing"].items()}
    if "sizes" in scaled:
        scaled["sizes"] = {key: scale_int(value, scale) for key, value in scaled["sizes"].items()}
    scaled["scale"] = scale
    return scaled
