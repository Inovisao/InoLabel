"""Mode badge — pill-shaped label for the annotation mode indicator."""

from __future__ import annotations

import tkinter as tk

from typing import Optional

from app.ui.theme.contrast import contrast_ratio
from app.ui.theme.tokens import COLORS, FONTS


def readable_fg(bg: str) -> str:
    """Texto claro ou escuro, o que tiver mais contraste com `bg`."""
    light, dark = COLORS["fg_light"], COLORS["text"]
    return light if contrast_ratio(light, bg) >= contrast_ratio(dark, bg) else dark


def make_badge(parent: tk.Widget, text: str, *, color: str, fg: Optional[str] = None) -> tk.Label:
    """Return a pill-shaped label with solid background.

    Parameters
    ----------
    color : background color hex string (e.g. COLORS["primary"])
    fg    : cor do texto; por padrao a de maior contraste com `color`
    """
    fg = fg or readable_fg(color)
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
