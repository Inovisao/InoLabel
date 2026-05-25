from app.annotation.shared import *
from app.ui.layout.responsive_window import apply_responsive_geometry
from app.ui.theme import COLORS, FONTS, SIZES, SPACING, install_scaled_theme


class MainWindowMixin:
    def _build_ui(self):
        self.window = tk.Tk()
        self.window.title(f"InoLabel — {self.task_mode.label}")
        self.window.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.ui = install_scaled_theme(self.window)
        self.window.configure(bg=COLORS["bg"])
        apply_responsive_geometry(self.window, width_ratio=0.92, height_ratio=0.90)

        self._initialize_ui_variables()
        self._initialize_theme()
        self._build_topbar()
        self._build_statusbar()
        self._build_body()
        self._bind_shortcuts()
        self.window.bind("<Configure>", self._on_window_resize)

    def _initialize_theme(self):
        self.theme = dict(COLORS)

    def _initialize_ui_variables(self):
        self.manual_id_var = tk.StringVar(value="")
        self.manual_class_var = tk.StringVar(value=(self.target_classes[0] if self.target_classes else ""))
        self.target_classes_var = tk.StringVar(value=", ".join(self.target_classes))
        self.image_name_var = tk.StringVar(value="-")
        self.info_var = tk.StringVar(
            value=f"{self.task_mode.label} · ROI opcional. Pressione R para definir 4 pontos."
        )

    def _on_window_resize(self, _event):
        if hasattr(self, "info_label"):
            available = max(320, self.window.winfo_width() - SIZES["sidebar_w"] - 240)
            if int(float(self.info_label.cget("wraplength") or 0)) != available:
                self.info_label.configure(wraplength=available)
        if self.current_frame is not None and not getattr(self, "export_screen_active", False):
            pending = getattr(self, "_resize_after_id", None)
            if pending is not None:
                try:
                    self.window.after_cancel(pending)
                except Exception:  # pylint: disable=broad-except
                    pass
            self._resize_after_id = self.window.after(120, self.update_display)

    @staticmethod
    def _button_options(width: int, state=tk.NORMAL) -> dict:
        return {
            "width": width, "state": state,
            "font": FONTS["button"],
            "padx": SIZES["btn_pad_x"], "pady": SIZES["btn_pad_y"],
            "bd": 0, "relief": tk.FLAT, "cursor": "hand2",
            "highlightthickness": 0,
        }

    def _apply_button_theme(self, button: tk.Button, *, bg: str, active_bg: str, fg: str = "#FFFFFF"):
        button.configure(
            bg=bg, fg=fg,
            activebackground=active_bg, activeforeground=fg,
            disabledforeground=COLORS["disabled_fg"],
        )
