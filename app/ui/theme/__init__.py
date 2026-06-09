from app.core.palette import CLASS_COLORS  # noqa: F401

COLORS: dict = {
    "primary": "#1560BD",
    "primary_dark": "#0D47A1",
    "secondary": "#F59E0B",
    "bg": "#1E1E2E",
    "bg_dark": "#13131F",
    "surface": "#2A2A3E",
    "border": "#3A3A5C",
    "text": "#E2E8F0",
    "text_muted": "#94A3B8",
    "danger": "#DC2626",
    "success": "#16A34A",
}

FONTS: dict = {
    "default": ("Segoe UI", 10),
    "heading": ("Segoe UI", 12, "bold"),
    "small": ("Segoe UI", 9),
    "mono": ("Consolas", 10),
}

SPACING: dict = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32,
}

SIZES: dict = {
    "button_height": 32,
    "input_height": 28,
    "sidebar_width": 220,
    "toolbar_height": 40,
    "panel_radius": 6,
}


def build_scaled_theme(scale: float = 1.0) -> dict:
    """Return a copy of the theme dicts scaled by *scale* (font sizes and spacing)."""
    def _scale(v: object) -> object:
        if isinstance(v, (int, float)):
            return int(v * scale)
        if isinstance(v, tuple):
            return tuple(int(x * scale) if isinstance(x, (int, float)) else x for x in v)
        return v

    return {
        "colors": dict(COLORS),
        "fonts": {k: _scale(v) for k, v in FONTS.items()},
        "spacing": {k: _scale(v) for k, v in SPACING.items()},
        "sizes": {k: _scale(v) for k, v in SIZES.items()},
    }
