"""OBB rendering utilities for visualizing rotated bounding boxes on canvas."""

from __future__ import annotations

import math
from typing import Any, Optional, Tuple

import numpy as np

from app.annotation_obb.geometry.obb_geometry import OBBDetection, obb_to_points


def draw_obb_on_canvas(
    canvas: Any,
    obb: OBBDetection,
    fill_color: str = "",
    outline_color: str = "red",
    width: int = 2,
    tag: str = "",
) -> Optional[int]:
    """
    Draw an OBB (oriented bounding box) on a Tkinter canvas with rotation visualization.

    Args:
        canvas: Tkinter canvas widget
        obb: OBBDetection object with cx, cy, w, h, angle
        fill_color: Fill color (empty = no fill)
        outline_color: Outline color (default: red)
        width: Line width (default: 2)
        tag: Canvas tag for grouping

    Returns:
        Canvas object ID or None if draw failed
    """
    try:
        points = obb_to_points(obb.cx, obb.cy, obb.width, obb.height, obb.angle)

        flat_coords = []
        for x, y in points:
            flat_coords.extend([float(x), float(y)])

        if len(flat_coords) < 8:
            return None

        kwargs = {
            "fill": fill_color,
            "outline": outline_color,
            "width": width,
        }
        if tag:
            kwargs["tag"] = tag

        return canvas.create_polygon(*flat_coords, **kwargs)
    except Exception as e:
        print(f"[ERRO] Falha ao desenhar OBB: {e}")
        return None


def draw_obb_center_marker(
    canvas: Any,
    obb: OBBDetection,
    color: str = "blue",
    size: int = 3,
    tag: str = "",
) -> Optional[int]:
    """
    Draw a small circle at the OBB center to show rotation origin.

    Args:
        canvas: Tkinter canvas widget
        obb: OBBDetection object
        color: Marker color (default: blue)
        size: Marker radius (default: 3)
        tag: Canvas tag

    Returns:
        Canvas object ID or None
    """
    try:
        x, y = obb.cx, obb.cy
        kwargs = {
            "fill": color,
            "outline": color,
        }
        if tag:
            kwargs["tag"] = tag

        return canvas.create_oval(
            x - size, y - size,
            x + size, y + size,
            **kwargs
        )
    except Exception as e:
        print(f"[ERRO] Falha ao desenhar marcador OBB: {e}")
        return None


def draw_obb_angle_indicator(
    canvas: Any,
    obb: OBBDetection,
    color: str = "green",
    length: float = 30,
    width: int = 2,
    tag: str = "",
) -> Optional[int]:
    """
    Draw an arrow from the OBB center showing the rotation angle.

    Args:
        canvas: Tkinter canvas widget
        obb: OBBDetection object with angle
        color: Arrow color (default: green)
        length: Arrow length in pixels (default: 30)
        width: Arrow width (default: 2)
        tag: Canvas tag

    Returns:
        Canvas object ID or None
    """
    try:
        angle_rad = math.radians(obb.angle)
        end_x = obb.cx + length * math.cos(angle_rad)
        end_y = obb.cy + length * math.sin(angle_rad)

        kwargs = {
            "fill": color,
            "width": width,
            "arrow": "last",
        }
        if tag:
            kwargs["tag"] = tag

        return canvas.create_line(
            obb.cx, obb.cy,
            end_x, end_y,
            **kwargs
        )
    except Exception as e:
        print(f"[ERRO] Falha ao desenhar indicador de ângulo: {e}")
        return None


def draw_obb_with_angle_label(
    canvas: Any,
    obb: OBBDetection,
    outline_color: str = "red",
    label_color: str = "white",
    tag: str = "",
) -> Tuple[Optional[int], Optional[int]]:
    """
    Draw an OBB and add a text label showing its rotation angle in degrees.

    Args:
        canvas: Tkinter canvas widget
        obb: OBBDetection object
        outline_color: OBB outline color
        label_color: Angle label text color
        tag: Canvas tag

    Returns:
        Tuple of (obb_id, label_id) or (None, None) if draw failed
    """
    try:
        obb_id = draw_obb_on_canvas(canvas, obb, outline_color=outline_color, tag=tag)

        angle_text = f"{obb.angle:.1f}°"
        label_id = canvas.create_text(
            obb.cx, obb.cy - 20,
            text=angle_text,
            fill=label_color,
            font=("Arial", 8, "bold"),
            tag=tag,
        )

        return obb_id, label_id
    except Exception as e:
        print(f"[ERRO] Falha ao desenhar OBB com rótulo: {e}")
        return None, None


class OBBCanvasRenderer:
    """Helper class to manage OBB rendering on canvas with multiple visualization options."""

    def __init__(self, canvas: Any):
        self.canvas = canvas
        self.obb_ids: dict[int, list[int]] = {}

    def render_obb(
        self,
        obb: OBBDetection,
        obb_id: int,
        show_center: bool = True,
        show_angle: bool = True,
        show_label: bool = True,
        colors: Optional[dict] = None,
    ) -> None:
        """
        Render a single OBB with optional center marker, angle indicator, and label.

        Args:
            obb: OBBDetection object
            obb_id: Unique identifier for this OBB (for tracking)
            show_center: Draw center marker
            show_angle: Draw angle indicator arrow
            show_label: Draw angle text label
            colors: Dict with keys 'outline', 'center', 'angle' for colors
        """
        if colors is None:
            colors = {"outline": "red", "center": "blue", "angle": "green"}

        canvas_ids = []

        main_id = draw_obb_on_canvas(
            self.canvas,
            obb,
            outline_color=colors.get("outline", "red"),
            width=2,
        )
        if main_id is not None:
            canvas_ids.append(main_id)

        if show_center:
            center_id = draw_obb_center_marker(
                self.canvas,
                obb,
                color=colors.get("center", "blue"),
            )
            if center_id is not None:
                canvas_ids.append(center_id)

        if show_angle:
            angle_id = draw_obb_angle_indicator(
                self.canvas,
                obb,
                color=colors.get("angle", "green"),
            )
            if angle_id is not None:
                canvas_ids.append(angle_id)

        if show_label:
            _, label_id = draw_obb_with_angle_label(
                self.canvas,
                obb,
                outline_color=colors.get("outline", "red"),
            )
            if label_id is not None:
                canvas_ids.append(label_id)

        if canvas_ids:
            self.obb_ids[obb_id] = canvas_ids

    def clear_obb(self, obb_id: int) -> None:
        """Remove all canvas elements for a specific OBB."""
        if obb_id in self.obb_ids:
            for canvas_id in self.obb_ids[obb_id]:
                try:
                    self.canvas.delete(canvas_id)
                except Exception:
                    pass
            del self.obb_ids[obb_id]

    def clear_all(self) -> None:
        """Remove all OBB visualizations."""
        for obb_id in list(self.obb_ids.keys()):
            self.clear_obb(obb_id)
