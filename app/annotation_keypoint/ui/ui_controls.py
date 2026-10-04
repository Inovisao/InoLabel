from app.annotation_keypoint.shared import *
from app.ui.theme.tokens import COLORS
from app.annotation.keybinds.keybind_mixin import KeybindMixin


class KPUIControlsMixin(KeybindMixin):
    def _bind_shortcuts(self):
        self.window.bind("<Escape>", lambda event: self._run_shortcut(event, self.on_escape))
        for key in "123456789":
            self.window.bind(key, self.on_class_shortcut)
        # Fixed keypoint instance controls
        self.window.bind("f", lambda e: self._run_shortcut(e, self.finish_instance))
        self.window.bind("x", lambda e: self._run_shortcut(e, self.skip_point))
        self.window.bind("c", lambda e: self._run_shortcut(e, self.cycle_next_visibility))
        self.window.bind("<BackSpace>", lambda e: self._run_shortcut(e, self.undo_last_point))
        # Label font size on the image
        for key in ("<plus>", "<equal>", "<KP_Add>"):
            self.window.bind(key, lambda e: self._run_shortcut(e, lambda: self.change_label_font(1)))
        for key in ("<minus>", "<KP_Subtract>"):
            self.window.bind(key, lambda e: self._run_shortcut(e, lambda: self.change_label_font(-1)))
        self.init_keybind_service()

    @staticmethod
    def _shortcut_is_text_input(event) -> bool:
        return isinstance(getattr(event, "widget", None), (tk.Entry, tk.Text))

    def _run_shortcut(self, event, action):
        if self._shortcut_is_text_input(event):
            return
        # Na tela de exportacao a anotacao esta suspensa: Enter/setas validariam ou
        # trocariam de frame enquanto o dataset e exportado.
        if getattr(self, "export_screen_active", False):
            return
        action()

    def _build_canvas(self):
        self.canvas = tk.Canvas(self.window, bg=COLORS["canvas_bg"], highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        self._bind_canvas_events()

    def _bind_canvas_events(self):
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)  # toggle keypoint visibility
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.on_pan_drag)
        self.canvas.bind("<ButtonRelease-2>", self.on_pan_end)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom)
        self.canvas.bind("<Command-MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)
        self.canvas.bind("<Button-5>", self.on_zoom)
        self.canvas.bind("<Control-Button-4>", self.on_zoom)
        self.canvas.bind("<Control-Button-5>", self.on_zoom)

    def enable_controls_after_roi(self):
        self.accept_button.config(state=tk.NORMAL)
        self.reject_button.config(state=tk.NORMAL)
        self.annotation_button.config(state=tk.NORMAL)
        self.remove_button.config(state=tk.NORMAL)
        self.selection_button.config(state=tk.NORMAL)
        self.pan_button.config(state=tk.NORMAL)
        self.apply_id_button.config(state=tk.DISABLED)
        self.edit_id_button.config(state=tk.NORMAL)  # repurposed: toggle point visibility
        self.export_dataset_button.config(state=tk.NORMAL)

    def disable_controls_for_roi(self):
        for name in (
            "accept_button", "reject_button", "annotation_button", "remove_button",
            "selection_button", "apply_id_button", "edit_id_button", "export_dataset_button",
        ):
            button = getattr(self, name, None)
            if button is not None:
                button.config(state=tk.DISABLED)

    def update_pan_button(self):
        self.sync_tool_toggle("pan_button", self.pan_mode)

    def update_annotation_button(self):
        self.sync_tool_toggle("annotation_button", self.annotation_mode)

    def update_remove_button(self):
        self.sync_tool_toggle("remove_button", self.remove_mode)

    def update_selection_button(self):
        self.sync_tool_toggle("selection_button", self.selection_mode)

    def update_edit_id_button(self):
        # Botao reaproveitado como acao de visibilidade do ponto, nao como modo.
        self.sync_tool_toggle("edit_id_button", False)
