from app.annotation.shared import *
from app.ui.theme.tokens import COLORS, FONTS, SIZES, SPACING


class StatusbarPanelMixin:
    def _build_statusbar(self):
        bar = tk.Frame(
            self.window,
            bg=COLORS["panel_alt"],
            height=SIZES["status_h"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self.status_source_var = tk.StringVar(value="")
        self.status_roi_var    = tk.StringVar(value="")
        self.status_mode_var   = tk.StringVar(value="")
        self.status_class_var  = tk.StringVar(value="")
        self.status_sel_var    = tk.StringVar(value="")

        def _block(var, *, fg=None, mono=False):
            font = FONTS["mono"] if mono else FONTS["status"]
            lbl = tk.Label(
                bar,
                textvariable=var,
                font=font,
                bg=COLORS["panel_alt"],
                fg=fg or COLORS["muted"],
                padx=SPACING["md"],
                pady=0,
                anchor="w",
            )
            lbl.pack(side=tk.LEFT, fill=tk.Y)
            return lbl

        def _sep():
            tk.Frame(bar, width=1, bg=COLORS["border"]).pack(
                side=tk.LEFT, fill=tk.Y, pady=8,
            )

        self.status_source_lbl = _block(self.status_source_var, fg=COLORS["text"], mono=True)
        _sep()
        self.status_roi_lbl   = _block(self.status_roi_var)
        _sep()
        self.status_mode_lbl  = _block(self.status_mode_var)
        _sep()
        self.status_class_lbl = _block(self.status_class_var)
        _sep()
        self.status_sel_lbl   = _block(self.status_sel_var)
