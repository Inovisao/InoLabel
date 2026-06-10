"""Small Tkinter component helpers used by legacy desktop screens."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


_BUTTON_COLORS = {
    "primary": {"bg": "#1560BD", "fg": "#FFFFFF"},
    "danger": {"bg": "#DC2626", "fg": "#FFFFFF"},
    "neutral": {"bg": "#F0F4FA", "fg": "#152040"},
    "accent": {"bg": "#F07820", "fg": "#FFFFFF"},
    "ghost": {"bg": "#FFFFFF", "fg": "#152040"},
}

_BUTTON_SIZES = {
    "sm": {"padx": 8, "pady": 3},
    "md": {"padx": 12, "pady": 6},
}


def make_btn(
    parent: tk.Misc,
    text: str,
    command: Callable[[], None],
    *,
    variant: str = "primary",
    size: str = "md",
    state: str = tk.NORMAL,
) -> tk.Button:
    colors = _BUTTON_COLORS.get(variant, _BUTTON_COLORS["primary"])
    sizing = _BUTTON_SIZES.get(size, _BUTTON_SIZES["md"])
    return tk.Button(
        parent,
        text=text,
        command=command,
        state=state,
        relief=tk.FLAT,
        activebackground=colors["bg"],
        activeforeground=colors["fg"],
        **colors,
        **sizing,
    )


def make_entry(parent: tk.Misc, textvariable: tk.StringVar, **kwargs) -> tk.Entry:
    return tk.Entry(parent, textvariable=textvariable, **kwargs)


def make_badge(parent: tk.Misc, text: str, *, color: str = "#1560BD") -> tk.Label:
    return tk.Label(parent, text=text, fg=color, bg="#FFFFFF", padx=6, pady=2)


from app.ui.components.card import Card  # noqa: E402

__all__ = ["Card", "make_badge", "make_btn", "make_entry"]
