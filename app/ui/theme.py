"""Compatibility shim — all content moved to app/ui/theme/tokens.py.

Existing imports such as `from app.ui.theme import COLORS` continue to work.
"""

from app.ui.theme import (  # noqa: F401
    COLORS,
    FONTS,
    SPACING,
    SIZES,
    TOKENS,
    CLASS_COLORS,
    build_scaled_theme,
    install_scaled_theme,
)
