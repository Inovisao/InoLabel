"""Pre-styled button factory with hover animation.

Usage:
    btn = make_btn(parent, "Validar", command=fn, variant="primary")
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Dict, Optional

from app.ui.theme.tokens import COLORS, FONTS, SIZES, SPACING

_VARIANTS: dict[str, dict] = {
    "primary": {
        "bg":        lambda: COLORS["primary"],
        "hover_bg":  lambda: COLORS["primary_active"],
        "active_bg": lambda: COLORS["primary_active"],
        "fg":        lambda: COLORS["fg_light"],
    },
    "danger": {
        "bg":        lambda: COLORS["danger"],
        "hover_bg":  lambda: COLORS["danger_active"],
        "active_bg": lambda: COLORS["danger_active"],
        "fg":        lambda: COLORS["fg_light"],
    },
    "neutral": {
        "bg":        lambda: COLORS["neutral"],
        "hover_bg":  lambda: COLORS["neutral_active"],
        "active_bg": lambda: COLORS["neutral_active"],
        "fg":        lambda: COLORS["text"],
    },
    "accent": {
        "bg":        lambda: COLORS["accent"],
        "hover_bg":  lambda: COLORS["accent_active"],
        "active_bg": lambda: COLORS["accent_active"],
        "fg":        lambda: COLORS["fg_light"],
    },
    "ghost": {
        "bg":        lambda: COLORS["panel"],
        "hover_bg":  lambda: COLORS["panel_alt"],
        "active_bg": lambda: COLORS["neutral"],
        "fg":        lambda: COLORS["muted"],
    },
}

# Slight opacity shift for "border" on ghost/neutral to give depth
_HOVER_BORDER: Dict[str, Optional[str]] = {
    "primary": None,
    "danger":  None,
    "neutral": COLORS["border"],
    "accent":  None,
    "ghost":   COLORS["border"],
}


def _attach_hover(btn: tk.Button, v: dict, variant: str) -> None:
    """Bind Enter/Leave for a smooth hover effect."""
    base_bg   = v["bg"]()
    hover_bg  = v["hover_bg"]()
    border    = _HOVER_BORDER.get(variant)

    def on_enter(_event):
        btn.configure(bg=hover_bg)
        if border:
            btn.configure(highlightbackground=border, highlightthickness=1)

    def on_leave(_event):
        btn.configure(bg=base_bg)
        if border:
            btn.configure(highlightthickness=0)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)


def make_btn(
    parent: tk.Widget,
    text: str,
    command: Optional[Callable] = None,
    *,
    variant: str = "neutral",
    size: str = "md",
    width: Optional[int] = None,
    anchor: str = tk.CENTER,
    state: str = tk.NORMAL,
) -> tk.Button:
    """Return a pre-styled tk.Button with hover animation.

    Parameters
    ----------
    variant : "primary" | "danger" | "neutral" | "accent" | "ghost"
    size    : "md" (default, 12pt bold) | "sm" (11pt caption, compact padding)
    """
    v    = _VARIANTS.get(variant, _VARIANTS["neutral"])
    font = FONTS["button"] if size == "md" else FONTS["caption"]
    padx = SIZES["btn_pad_x"] if size == "md" else SPACING["sm"]
    pady = SIZES["btn_pad_y"] if size == "md" else 4
    kw: dict = dict(
        text=text,
        font=font,
        padx=padx,
        pady=pady,
        bd=0,
        relief=tk.FLAT,
        cursor="hand2",
        highlightthickness=0,
        anchor=anchor,
        bg=v["bg"](),
        fg=v["fg"](),
        activebackground=v["active_bg"](),
        activeforeground=v["fg"](),
        disabledforeground=COLORS["disabled_fg"],
        state=state,
    )
    if command is not None:
        kw["command"] = command
    if width is not None:
        kw["width"] = width

    btn = tk.Button(parent, **kw)
    if state == tk.NORMAL:
        _attach_hover(btn, v, variant)
    return btn
