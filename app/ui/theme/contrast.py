"""Contraste WCAG 2.1 entre duas cores hex."""

from __future__ import annotations


def _channel(value: int) -> float:
    c = value / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    clean = color.strip().lstrip("#")
    if len(clean) != 6:
        raise ValueError(f"Cor hex invalida: {color!r}")
    r, g, b = (int(clean[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """Razao de contraste (1.0 a 21.0); AA exige >= 4.5 para texto normal."""
    la, lb = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)
