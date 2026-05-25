"""Compatibility re-export — existing code using `from app.ui.theme import X` keeps working."""

from app.ui.theme.tokens import (  # noqa: F401
    COLORS,
    FONTS,
    SPACING,
    SIZES,
    TOKENS,
    build_scaled_theme,
    install_scaled_theme,
)
from app.ui.theme.palette import CLASS_COLORS  # noqa: F401
