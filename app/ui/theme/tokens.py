"""Design tokens — single source of truth for colors, typography, spacing and sizes."""

from __future__ import annotations

import tkinter.font as _tkfont

from app.ui.layout.scale import apply_scale, compute_ui_scale, get_screen_dpi

COLORS: dict[str, str] = {
    # Backgrounds
    "bg":             "#F0F4FA",
    "panel":          "#FFFFFF",
    "panel_alt":      "#EEF3FB",
    # Borders
    "border":         "#C2D0E8",
    # Text
    "text":           "#152040",
    "muted":          "#526A88",
    "fg_light":       "#FFFFFF",
    "disabled_fg":    "#B8C8DC",
    # Actions — primary (blue)
    "primary":        "#1560BD",
    "primary_active": "#0D47A1",
    # Actions — danger (red)
    "danger":         "#C62828",
    "danger_active":  "#B71C1C",
    # Actions — neutral (gray)
    "neutral":        "#DDE5F0",
    "neutral_active": "#C8D4E8",
    # Actions — accent (orange)
    "accent":         "#F07820",
    "accent_active":  "#D96A10",
    # Inputs
    "input_bg":       "#F8FBFF",
    # Canvas
    "canvas_bg":      "#16130f",
}

FONTS: dict[str, tuple] = {
    "title":   ("Helvetica", 22, "bold"),
    "heading": ("Helvetica", 15, "bold"),
    "subhead": ("Helvetica", 13, "bold"),
    "button":  ("Helvetica", 12, "bold"),
    "body":    ("Helvetica", 12),
    "label":   ("Helvetica", 12, "bold"),
    "caption": ("Helvetica", 11),
    "tag":     ("Helvetica", 11, "bold"),
    "status":  ("Helvetica", 11),
    "mono":    ("Courier", 11),
}

SPACING: dict[str, int] = {
    "xs":   4,
    "sm":   8,
    "md":  16,
    "lg":  24,
    "xl":  32,
    "2xl": 48,
}

SIZES: dict[str, int] = {
    "sidebar_w":      320,
    "sidebar_min_w":  300,
    "sidebar_max_w":  390,
    "topbar_h":        56,
    "status_h":        40,
    "btn_pad_x":       14,
    "btn_pad_y":       10,
    "btn_h":           44,
    "btn_h_sm":        36,
    "input_pad":        8,
    "content_max_w": 1080,
    "content_min_w":  760,
}

TOKENS: dict = {
    "colors":  COLORS,
    "fonts":   FONTS,
    "spacing": SPACING,
    "sizes":   SIZES,
}

_BASE_TOKENS: dict = {
    "colors":  dict(COLORS),
    "fonts":   dict(FONTS),
    "spacing": dict(SPACING),
    "sizes":   dict(SIZES),
}


def build_scaled_theme(root=None, scale: float | None = None) -> dict:
    """Return scaled theme tokens from an explicit scale or a Tk root."""
    if scale is None:
        scale = (
            compute_ui_scale(root.winfo_screenheight(), get_screen_dpi(root))
            if root is not None
            else 1.0
        )
    theme = apply_scale(_BASE_TOKENS, scale)
    theme["colors"] = dict(_BASE_TOKENS["colors"])
    return theme


def install_scaled_theme(root=None, scale: float | None = None) -> dict:
    """Scale module-level dicts in-place and propagate to Tk dialogs."""
    theme = build_scaled_theme(root=root, scale=scale)
    COLORS.clear();  COLORS.update(theme["colors"])
    FONTS.clear();   FONTS.update(theme["fonts"])
    SPACING.clear(); SPACING.update(theme["spacing"])
    SIZES.clear();   SIZES.update(theme["sizes"])

    if root is not None:
        body_size = theme["fonts"]["body"][1]
        root.option_add("*Font", f"Helvetica {body_size}", "userDefault")
        for _name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                      "TkHeadingFont", "TkFixedFont", "TkIconFont"):
            try:
                _tkfont.nametofont(_name).configure(family="Helvetica", size=body_size)
            except Exception:  # pylint: disable=broad-except
                pass

    return theme
