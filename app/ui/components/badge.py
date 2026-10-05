"""Mode badge — pill-shaped label for the annotation mode indicator."""

from __future__ import annotations

import tkinter as tk

from app.ui.theme.tokens import COLORS, FONTS


def make_badge(parent: tk.Widget, text: str, *, color: str) -> tk.Label:
    """Return a pill-shaped label with solid background.

    Parameters
    ----------
    color : background color hex string (e.g. COLORS["primary"])
    """
    fg = COLORS["fg_light"]
    return tk.Label(
        parent,
        text=text,
        font=FONTS["tag"],
        bg=color,
        fg=fg,
        padx=10,
        pady=4,
        relief=tk.FLAT,
        bd=0,
    )
