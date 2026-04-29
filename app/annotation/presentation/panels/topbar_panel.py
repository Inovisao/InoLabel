from app.annotation.shared import *
from app.ui.theme import COLORS, FONTS, SPACING


class TopbarPanelMixin:
    def _build_topbar(self):
        bar = tk.Frame(
            self.window, bg=COLORS["panel"],
            highlightbackground=COLORS["border"], highlightthickness=1, bd=0,
        )
        bar.pack(fill=tk.X, side=tk.TOP)

        inner = tk.Frame(bar, bg=COLORS["panel"])
        inner.pack(fill=tk.X, padx=SPACING["md"], pady=SPACING["sm"])

        badge_bg = COLORS["primary"] if self.task_mode.value == "tracking" else COLORS["accent"]
        tk.Label(
            inner,
            text=f"  {self.task_mode.label}  ",
            font=FONTS["caption"],
            bg=badge_bg, fg=COLORS["fg_light"],
            padx=SPACING["sm"], pady=3,
            relief=tk.FLAT, bd=0,
        ).pack(side=tk.LEFT, padx=(0, SPACING["md"]))

        self.info_label = tk.Label(
            inner,
            textvariable=self.info_var,
            font=FONTS["body"],
            bg=COLORS["panel"], fg=COLORS["text"],
            wraplength=max(320, self.window.winfo_width() - 540),
            justify=tk.LEFT, anchor="w",
        )
        self.info_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, SPACING["md"]))

        self.image_name_label = tk.Label(
            inner,
            textvariable=self.image_name_var,
            font=FONTS["caption"],
            bg=COLORS["panel"], fg=COLORS["muted"],
        )
        self.image_name_label.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))

        self.help_button = self._topbar_btn(inner, "Help", lambda: None)
        self.help_button.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))
        self._apply_button_theme(
            self.help_button,
            bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self._attach_help_tooltip(self.help_button)

        self.key_mapping_button = self._topbar_btn(inner, "Mapeamento: Setas", self.open_key_mapping_dialog)
        self.key_mapping_button.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))
        self._apply_button_theme(
            self.key_mapping_button,
            bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )

        self.open_folder_button = self._topbar_btn(inner, "Ver em folder", self.on_open_in_folder, state=tk.DISABLED)
        self.open_folder_button.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))
        self._apply_button_theme(
            self.open_folder_button,
            bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )

        self.delete_image_button = self._topbar_btn(inner, "Deletar", self.on_delete_image, state=tk.DISABLED)
        self.delete_image_button.pack(side=tk.LEFT)
        self._apply_button_theme(
            self.delete_image_button,
            bg=COLORS["danger"], active_bg=COLORS["danger_active"],
        )

    def _topbar_btn(self, parent, text: str, command, *, state=tk.NORMAL):
        return tk.Button(
            parent, text=text, command=command,
            font=FONTS["caption"],
            padx=SPACING["sm"], pady=3,
            bd=0, relief=tk.FLAT, cursor="hand2",
            highlightthickness=0, state=state,
        )

    # ── tooltip de ajuda ───────────────────────────────────────────

    def _attach_help_tooltip(self, widget):
        def build_help_text():
            if getattr(self, "key_mapping_mode", "arrows") == "wasd":
                nav = "W/A: voltar imagem salva\nS/D: avancar imagem salva\nSelecao: use o botao lateral"
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
                justify=tk.LEFT, anchor="w",
                font=FONTS["caption"],
                bg=COLORS["panel"], fg=COLORS["text"],
                padx=SPACING["sm"], pady=SPACING["sm"],
                relief=tk.SOLID, bd=1,
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

    # ── diálogo de mapeamento de teclas ───────────────────────────

    def open_key_mapping_dialog(self):
        existing = getattr(self, "_key_mapping_dialog", None)
        if existing is not None:
            try:
                existing.lift()
                existing.focus_force()
                return
            except Exception:  # pylint: disable=broad-except
                self._key_mapping_dialog = None

        dialog = tk.Toplevel(self.window)
        self._key_mapping_dialog = dialog
        dialog.title("Mapeamento de teclas")
        dialog.configure(bg=COLORS["panel"])
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._close_key_mapping_dialog(dialog))

        x = self.key_mapping_button.winfo_rootx()
        y = self.key_mapping_button.winfo_rooty() + self.key_mapping_button.winfo_height() + 8
        dialog.geometry(f"640x360+{x}+{y}")
        dialog.minsize(640, 360)

        panel = tk.Frame(dialog, bg=COLORS["panel"], padx=SPACING["md"], pady=SPACING["md"])
        panel.pack(fill=tk.BOTH, expand=True)
        panel.grid_columnconfigure(0, weight=1)

        tk.Label(
            panel,
            text="Navegacao entre imagens",
            font=FONTS["label"],
            bg=COLORS["panel"], fg=COLORS["text"],
            anchor="w", justify=tk.LEFT,
        ).grid(row=0, column=0, sticky="ew")

        tk.Label(
            panel,
            text="Escolha se a navegacao usa setas ou WASD, como em jogos.",
            font=FONTS["caption"],
            bg=COLORS["panel"], fg=COLORS["muted"],
            anchor="w", justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="ew", pady=(2, SPACING["md"]))

        arrows_button = self._mapping_option_button(
            panel,
            "Setas",
            "Anterior: Left    Proximo: Right    Selecao: S",
            lambda: self._select_key_mapping("arrows", dialog),
        )
        arrows_button.grid(row=2, column=0, sticky="ew", pady=(0, SPACING["xs"]))

        wasd_button = self._mapping_option_button(
            panel,
            "WASD",
            "Anterior: W ou A    Proximo: S ou D    Selecao: botao lateral",
            lambda: self._select_key_mapping("wasd", dialog),
        )
        wasd_button.grid(row=3, column=0, sticky="ew")

        actions = tk.Frame(panel, bg=COLORS["panel"])
        actions.grid(row=4, column=0, sticky="ew", pady=(SPACING["sm"], 0))
        actions.grid_columnconfigure(0, weight=1)
        close_button = self._topbar_btn(actions, "Fechar", lambda: self._close_key_mapping_dialog(dialog))
        close_button.grid(row=0, column=1, sticky="e")
        self._apply_button_theme(
            close_button,
            bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        dialog.lift()
        dialog.focus_force()

    def _mapping_option_button(self, parent, title: str, body: str, command):
        text = f"{title}    {body}"
        button = tk.Button(
            parent,
            text=text,
            command=command,
            justify=tk.LEFT, anchor="w",
            font=FONTS["body"],
            padx=SPACING["md"], pady=SPACING["xs"],
            bd=0, relief=tk.FLAT, cursor="hand2",
            highlightthickness=1, highlightbackground=COLORS["border"],
            wraplength=560,
        )
        self._apply_button_theme(
            button,
            bg=COLORS["panel_alt"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        return button

    def _select_key_mapping(self, mode: str, dialog):
        self.apply_key_mapping(mode)
        self.info_var.set("Mapeamento WASD ativo." if mode == "wasd" else "Mapeamento por setas ativo.")
        self._close_key_mapping_dialog(dialog)

    def _close_key_mapping_dialog(self, dialog):
        if getattr(self, "_key_mapping_dialog", None) is dialog:
            self._key_mapping_dialog = None
        try:
            dialog.destroy()
        except Exception:  # pylint: disable=broad-except
            pass
