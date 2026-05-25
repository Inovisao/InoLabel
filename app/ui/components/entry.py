"""Styled entry field."""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from app.ui.theme.tokens import COLORS, FONTS, SIZES


def make_entry(
    parent: tk.Widget,
    variable: tk.StringVar,
    *,
    width: Optional[int] = None,
) -> tk.Entry:
    """Return a consistently styled tk.Entry."""
    kw: dict = dict(
        textvariable=variable,
        font=FONTS["body"],
        bg=COLORS["input_bg"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["accent"],
        bd=SIZES["input_pad"],
    )
    if width is not None:
        kw["width"] = width
    return tk.Entry(parent, **kw)
