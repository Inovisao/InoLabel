from app.annotation.shared import *


class UIControlsMixin:
    def _bind_shortcuts(self):
        self.window.bind("<Return>", lambda event: self.on_accept())
        self.window.bind("<space>", lambda event: self.on_reject())
        self.window.bind("<Escape>", lambda event: self.on_quit())
        self.window.bind("k", lambda event: self.toggle_annotation_mode())
        self.window.bind("K", lambda event: self.toggle_annotation_mode())
        self.window.bind("r", lambda event: self.reset_roi())
        self.window.bind("R", lambda event: self.reset_roi())
        self.window.bind("e", lambda event: self.toggle_edit_id_mode())
        self.window.bind("E", lambda event: self.toggle_edit_id_mode())
        self.window.bind("<Left>", lambda event: self.on_prev_saved())
        self.window.bind("<Right>", lambda event: self.on_next_saved())

    def _build_canvas(self):
        self.canvas = tk.Canvas(self.window, bg="black", highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def enable_controls_after_roi(self):
        """Habilita botoes apos definir ROI."""
        self.accept_button.config(state=tk.NORMAL)
        self.reject_button.config(state=tk.NORMAL)
        self.annotation_button.config(state=tk.NORMAL)
        self.remove_button.config(state=tk.NORMAL)
        self.apply_id_button.config(state=tk.NORMAL)
        self.edit_id_button.config(state=tk.NORMAL)
        self.save_yaml_button.config(state=tk.NORMAL)
        self.save_coco_button.config(state=tk.NORMAL)
        self.info_var.set(self.build_status_message())

    def disable_controls_for_roi(self):
        """Desabilita botoes enquanto ROI nao for definido."""
        self.accept_button.config(state=tk.DISABLED)
        self.reject_button.config(state=tk.DISABLED)
        self.annotation_button.config(state=tk.DISABLED)
        self.remove_button.config(state=tk.DISABLED)
        self.apply_id_button.config(state=tk.DISABLED)
        self.edit_id_button.config(state=tk.DISABLED)
        self.save_yaml_button.config(state=tk.DISABLED)
        self.save_coco_button.config(state=tk.DISABLED)

    def update_annotation_button(self):
        """Atualiza o texto do botao de modo de anotacao."""
        if hasattr(self, "annotation_button"):
            estado = "ON" if self.annotation_mode else "OFF"
            self.annotation_button.config(text=f"Modo anotacao {estado} (K)")

    def update_remove_button(self):
        """Atualiza o texto do botao de remocao."""
        if hasattr(self, "remove_button"):
            estado = "ON" if self.remove_mode else "OFF"
            self.remove_button.config(text=f"Remover anotacao {estado}")

    def update_edit_id_button(self):
        """Atualiza o texto do botao de edicao de ID."""
        if hasattr(self, "edit_id_button"):
            estado = "ON" if self.edit_id_mode else "OFF"
            self.edit_id_button.config(text=f"Editar ID {estado} (E)")

    # ===================== EVENTOS DE MOUSE =====================
