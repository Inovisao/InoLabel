from app.annotation.shared import *
from app.ui.components import make_annotation_canvas


class CanvasPanelMixin:
    def _build_canvas_area(self, parent):
        self.canvas_frame = parent
        self.canvas_shell = parent
        self.canvas_card  = parent

        self.canvas = make_annotation_canvas(parent)
        self.canvas.pack(expand=True, anchor=tk.CENTER)
        self._bind_canvas_events()
