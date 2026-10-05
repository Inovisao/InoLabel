"""Card primitive for legacy Tkinter screens."""

from __future__ import annotations

import tkinter as tk


class Card(tk.Frame):
    def __init__(self, parent: tk.Misc, **kwargs):
        defaults = {"bg": "#FFFFFF", "bd": 1, "relief": tk.SOLID}
        defaults.update(kwargs)
        super().__init__(parent, **defaults)
