"""Layout separators and section labels."""

from __future__ import annotations

import tkinter as tk

from app.ui.theme.tokens import COLORS, FONTS, SPACING


def hsep(parent: tk.Widget, *, pady: int = 0) -> tk.Frame:
    """Horizontal 1px separator line."""
    frame = tk.Frame(parent, height=1, bg=COLORS["border"])
    if pady:
        frame.pack(fill=tk.X, pady=pady)
    return frame


def section_label(parent: tk.Widget, text: str) -> tk.Label:
    """Uppercase section title for sidebar groupings."""
    return tk.Label(
        parent,
        text=text.upper(),
        font=FONTS["caption"],
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        anchor="w",
        padx=SPACING["sm"],
    )
