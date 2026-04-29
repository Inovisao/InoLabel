from app.annotation.shared import *
from app.ui.theme import COLORS, FONTS, SPACING


class StatusbarPanelMixin:
    def _build_statusbar(self):
        bar = tk.Frame(
            self.window, bg=COLORS["panel_alt"],
            highlightbackground=COLORS["border"], highlightthickness=1, bd=0,
        )
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_source_var = tk.StringVar(value="")
        self.status_roi_var    = tk.StringVar(value="")
        self.status_mode_var   = tk.StringVar(value="")
        self.status_class_var  = tk.StringVar(value="")
        self.status_sel_var    = tk.StringVar(value="")

        def _block(var, fg=None):
            lbl = tk.Label(
                bar, textvariable=var,
                font=FONTS["status"],
                bg=COLORS["panel_alt"],
                fg=fg or COLORS["muted"],
                padx=SPACING["md"], pady=SPACING["sm"],
            )
            lbl.pack(side=tk.LEFT, fill=tk.Y)
            return lbl

        def _sep():
            tk.Frame(bar, width=1, bg=COLORS["border"]).pack(
                side=tk.LEFT, fill=tk.Y, pady=6,
            )

        self.status_source_lbl = _block(self.status_source_var, COLORS["text"])
        _sep()
        self.status_roi_lbl   = _block(self.status_roi_var)
        _sep()
        self.status_mode_lbl  = _block(self.status_mode_var)
        _sep()
        self.status_class_lbl = _block(self.status_class_var)
        _sep()
        self.status_sel_lbl   = _block(self.status_sel_var)
