from app.annotation.shared import *
from app.ui.components import make_badge, make_btn
from app.ui.theme.tokens import COLORS, FONTS, SPACING


class TopbarPanelMixin:
    def _build_topbar(self):
        bar = tk.Frame(
            self.window,
            bg=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        bar.pack(fill=tk.X, side=tk.TOP)

        inner = tk.Frame(bar, bg=COLORS["panel"])
        inner.pack(fill=tk.X, padx=SPACING["md"], pady=SPACING["sm"])

        # Mode badge — blue for tracking/detection/obb, orange for classification
        badge_color = (
            COLORS["accent"]
            if self.task_mode.value == "classification"
            else COLORS["primary"]
        )
        make_badge(inner, self.task_mode.label, color=badge_color).pack(
            side=tk.LEFT, padx=(0, SPACING["md"])
        )

        self.info_label = tk.Label(
            inner,
            textvariable=self.info_var,
            font=FONTS["body"],
            bg=COLORS["panel"],
            fg=COLORS["text"],
            wraplength=max(320, self.window.winfo_width() - 540),
            justify=tk.LEFT,
            anchor="w",
        )
        self.info_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, SPACING["md"]))

        self.image_name_label = tk.Label(
            inner,
            textvariable=self.image_name_var,
            font=FONTS["caption"],
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        )
        self.image_name_label.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))

        self.help_button = make_btn(inner, "Ajuda", lambda: None, variant="ghost", size="sm")
        self.help_button.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))
        self._attach_help_tooltip(self.help_button)

        self.key_mapping_button = make_btn(
            inner, "Atalhos: arrows", self.open_keybind_editor, variant="ghost", size="sm"
        )
        self.key_mapping_button.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))

        self.open_folder_button = make_btn(
            inner, "Ver em folder", self.on_open_in_folder, variant="ghost", size="sm", state=tk.DISABLED
        )
        self.open_folder_button.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))

        self.delete_image_button = make_btn(
            inner, "Deletar", self.on_delete_image, variant="danger", size="sm", state=tk.DISABLED
        )
        self.delete_image_button.pack(side=tk.LEFT)

    # ── tooltip de ajuda ───────────────────────────────────────────

    def _attach_help_tooltip(self, widget):
        def build_help_text():
            service = getattr(self, "_keybind_service", None)
            if service is not None:
                profile = service.get_active_profile()
                from app.annotation.keybinds.keybind_editor import _display_key
                from app.annotation.keybinds.actions import ACTION_REGISTRY

                def key_for(action_id: str) -> str:
                    k = profile.get_key(action_id) or ""
                    return _display_key(k)

                nav = (
                    f"{key_for('prev_frame')}: frame anterior    "
                    f"{key_for('next_frame')}: próximo frame\n"
                    f"{key_for('toggle_selection')}: selecionar anotação"
                )
            else:
                nav = "Setas: navegar imagens salvas\nS: selecionar anotacao"
            return (
                "Atalhos\n"
                "Enter: validar imagem\n"
                "Espaco: rejeitar/avancar\n"
                "K: ligar/desligar anotacao manual\n"
                "H: ligar/desligar mover imagem\n"
                "Scroll: zoom no cursor\n"
                "Botao do meio + arrastar: mover imagem\n"
                "Ctrl+0: ajustar imagem na tela\n"
                f"{nav}\n"
                "E: editar ID\n"
                "R: redefinir ROI\n"
                "Ctrl+Z: desfazer\n"
                "1-9: trocar classe ativa\n"
                "Esc: sair"
            )

        def show(_event=None):
            self._hide_help_tooltip()
            tip = tk.Toplevel(self.window)
            tip.wm_overrideredirect(True)
            tip.configure(bg=COLORS["panel"], padx=1, pady=1)
            x = widget.winfo_rootx()
            y = widget.winfo_rooty() + widget.winfo_height() + 6
            tip.geometry(f"+{x}+{y}")
            tk.Label(
                tip,
                text=build_help_text(),
                justify=tk.LEFT,
                anchor="w",
                font=FONTS["caption"],
                bg=COLORS["panel"],
                fg=COLORS["text"],
                padx=SPACING["sm"],
                pady=SPACING["sm"],
                relief=tk.SOLID,
                bd=1,
            ).pack()
            self._help_tooltip = tip

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", lambda _event: self._hide_help_tooltip())

    def _hide_help_tooltip(self):
        tip = getattr(self, "_help_tooltip", None)
        if tip is None:
            return
        try:
            tip.destroy()
        except Exception:  # pylint: disable=broad-except
            pass
        self._help_tooltip = None
