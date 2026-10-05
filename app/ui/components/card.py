"""Card container — frame with subtle border and consistent padding."""

from __future__ import annotations

import tkinter as tk

from app.ui.theme.tokens import COLORS, SPACING


class Card(tk.Frame):
    """A visually grouped container with border and inner padding."""

    def __init__(self, parent: tk.Widget, *, padx: int | None = None, pady: int | None = None, **kw):
        padx = padx if padx is not None else SPACING["lg"]
        pady = pady if pady is not None else SPACING["lg"]
        super().__init__(
            parent,
            bg=kw.pop("bg", COLORS["panel"]),
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
            padx=padx,
            pady=pady,
            **kw,
        )
