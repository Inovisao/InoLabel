"""Annotation canvas factory."""

from __future__ import annotations

import tkinter as tk

from app.ui.theme.tokens import COLORS


def make_annotation_canvas(parent: tk.Widget) -> tk.Canvas:
    """Return a canvas configured for image annotation (dark background)."""
    return tk.Canvas(parent, bg=COLORS["canvas_bg"], highlightthickness=0)
