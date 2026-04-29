from app.annotation.shared import *
from app.ui.theme import COLORS


class CanvasPanelMixin:
    def _build_canvas_area(self, parent):
        self.canvas_frame = parent
        self.canvas_shell = parent
        self.canvas_card  = parent

        self.canvas = tk.Canvas(parent, bg=COLORS["canvas_bg"], highlightthickness=0)
        self.canvas.pack(expand=True, anchor=tk.CENTER)
        self._bind_canvas_events()
