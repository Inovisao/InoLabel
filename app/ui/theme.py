"""Central design tokens - single source of truth for UI proportions."""

from __future__ import annotations

from app.ui.layout.scale import apply_scale, compute_ui_scale, get_screen_dpi

COLORS = {
    "bg":              "#f3efe7",
    "panel":           "#fffaf2",
    "panel_alt":       "#f7f1e6",
    "border":          "#d8cdbd",
    "text":            "#2d2418",
    "muted":           "#6e6252",
    "primary":         "#215732",
    "primary_active":  "#184525",
    "danger":          "#9f3a2a",
    "danger_active":   "#7f2d21",
    "neutral":         "#d9c6a5",
    "neutral_active":  "#cdb58e",
    "accent":          "#d3a64f",
    "accent_active":   "#bf913f",
    "input_bg":        "#fffdf8",
    "canvas_bg":       "#16130f",
    "fg_light":        "#fffaf2",
    "disabled_fg":     "#eadfce",
}

FONTS = {
    "title":   ("Helvetica", 22, "bold"),
    "heading": ("Helvetica", 15, "bold"),
    "subhead": ("Helvetica", 13, "bold"),
    "button":  ("Helvetica", 12, "bold"),
    "body":    ("Helvetica", 12),
    "label":   ("Helvetica", 12, "bold"),
    "caption": ("Helvetica", 11),
    "tag":     ("Helvetica", 11, "bold"),
    "status":  ("Helvetica", 11),
}

SPACING = {
    "xs":   4,
    "sm":   8,
    "md":  14,
    "lg":  20,
    "xl":  32,
    "2xl": 48,
}

SIZES = {
    "sidebar_w":       320,
    "sidebar_min_w":   300,
    "sidebar_max_w":   390,
    "topbar_h":         58,
    "status_h":         38,
    "btn_pad_x":        14,
    "btn_pad_y":        10,
    "input_pad":         8,
    "content_max_w":   920,
    "content_min_w":   680,
}

TOKENS = {
    "colors": COLORS,
    "fonts": FONTS,
    "spacing": SPACING,
    "sizes": SIZES,
}

_BASE_TOKENS = {
    "colors": dict(COLORS),
    "fonts": dict(FONTS),
    "spacing": dict(SPACING),
    "sizes": dict(SIZES),
}


def build_scaled_theme(root=None, scale: float | None = None) -> dict:
    """Build scaled theme tokens from an explicit scale or a Tk root."""

    if scale is None:
        if root is None:
            scale = 1.0
        else:
            scale = compute_ui_scale(root.winfo_screenheight(), get_screen_dpi(root))
    theme = apply_scale(_BASE_TOKENS, scale)
    theme["colors"] = dict(_BASE_TOKENS["colors"])
    return theme


def install_scaled_theme(root=None, scale: float | None = None) -> dict:
    """Scale module-level token dictionaries in place and return the theme."""

    theme = build_scaled_theme(root=root, scale=scale)
    COLORS.clear()
    COLORS.update(theme["colors"])
    FONTS.clear()
    FONTS.update(theme["fonts"])
    SPACING.clear()
    SPACING.update(theme["spacing"])
    SIZES.clear()
    SIZES.update(theme["sizes"])
    return theme
