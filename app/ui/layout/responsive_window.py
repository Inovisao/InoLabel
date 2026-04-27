"""Responsive Tk window helpers."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenMetrics:
    width: int
    height: int
    window_width: int
    window_height: int


def measure_screen(root: tk.Tk, width_ratio: float = 0.82, height_ratio: float = 0.82) -> ScreenMetrics:
    """Calculate a comfortable initial size for the current monitor."""

    screen_w = max(800, int(root.winfo_screenwidth()))
    screen_h = max(600, int(root.winfo_screenheight()))
    win_w = min(screen_w - 40, max(720, int(screen_w * width_ratio)))
    win_h = min(screen_h - 60, max(520, int(screen_h * height_ratio)))
    return ScreenMetrics(screen_w, screen_h, win_w, win_h)


def apply_responsive_geometry(root: tk.Tk, *, width_ratio: float = 0.82, height_ratio: float = 0.82):
    """Set initial geometry, min size, and max size based on monitor dimensions."""

    metrics = measure_screen(root, width_ratio=width_ratio, height_ratio=height_ratio)
    x = max(0, (metrics.width - metrics.window_width) // 2)
    y = max(0, (metrics.height - metrics.window_height) // 2)
    root.geometry(f"{metrics.window_width}x{metrics.window_height}+{x}+{y}")
    root.minsize(min(680, metrics.width - 40), min(480, metrics.height - 60))
    root.maxsize(metrics.width, metrics.height)
    return metrics

