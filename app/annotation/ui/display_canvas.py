"""Canvas helpers for legacy annotation workflows."""

from __future__ import annotations


class DisplayCanvasMixin:
    """Pan/zoom math shared by legacy tests and Tkinter canvas code."""

    def clamp_zoom_pan(
        self,
        scaled_width: float,
        scaled_height: float,
        viewport_width: float,
        viewport_height: float,
        min_pan_x: float,
        min_pan_y: float,
    ) -> None:
        if scaled_width <= viewport_width:
            self.zoom_pan_x = 0
        else:
            self.zoom_pan_x = max(min_pan_x, min(-min_pan_x, self.zoom_pan_x))

        if scaled_height <= viewport_height:
            self.zoom_pan_y = 0
        else:
            self.zoom_pan_y = max(min_pan_y, min(-min_pan_y, self.zoom_pan_y))
