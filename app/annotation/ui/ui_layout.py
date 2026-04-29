from app.annotation.shared import *
from app.ui.layout.responsive_window import apply_responsive_geometry
from app.ui.layout.scrollable_frame import ScrollableFrame
from app.ui.theme import COLORS, FONTS, SIZES, SPACING, install_scaled_theme


class UILayoutMixin:
    def _build_ui(self):
        self.window = tk.Tk()
        self.window.title(f"Validador — {self.task_mode.label}")
        self.window.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.ui = install_scaled_theme(self.window)
        self.window.configure(bg=COLORS["bg"])
        apply_responsive_geometry(self.window, width_ratio=0.92, height_ratio=0.90)

        self._initialize_ui_variables()
        self._initialize_theme()
        self._build_topbar()
        self._build_statusbar()   # pack BOTTOM first so it stays below the body
        self._build_body()
        self._bind_shortcuts()
        self.window.bind("<Configure>", self._on_window_resize)

    def _initialize_theme(self):
        # Instance dict so other mixins can still read self.theme["key"]
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
        if self.current_frame is not None:
            pending = getattr(self, "_resize_after_id", None)
            if pending is not None:
                try:
                    self.window.after_cancel(pending)
                except Exception:  # pylint: disable=broad-except
                    pass
            self._resize_after_id = self.window.after(120, self.update_display)

    # ── Top bar ────────────────────────────────────────────────────

    def _build_topbar(self):
        bar = tk.Frame(
            self.window, bg=COLORS["panel"],
            highlightbackground=COLORS["border"], highlightthickness=1, bd=0,
        )
        bar.pack(fill=tk.X, side=tk.TOP)

        inner = tk.Frame(bar, bg=COLORS["panel"])
        inner.pack(fill=tk.X, padx=SPACING["md"], pady=SPACING["sm"])

        # Mode badge
        badge_bg = COLORS["primary"] if self.task_mode.value == "tracking" else COLORS["accent"]
        tk.Label(
            inner,
            text=f"  {self.task_mode.label}  ",
            font=FONTS["caption"],
            bg=badge_bg, fg=COLORS["fg_light"],
            padx=SPACING["sm"], pady=3,
            relief=tk.FLAT, bd=0,
        ).pack(side=tk.LEFT, padx=(0, SPACING["md"]))

        # Feedback / info label (fills center)
        self.info_label = tk.Label(
            inner,
            textvariable=self.info_var,
            font=FONTS["body"],
            bg=COLORS["panel"], fg=COLORS["text"],
            wraplength=max(320, self.window.winfo_width() - SIZES["sidebar_w"] - 240),
            justify=tk.LEFT, anchor="w",
        )
        self.info_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, SPACING["md"]))

        # Image controls (right side)
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
            bg=COLORS["panel"],
            fg=COLORS["text"],
            anchor="w",
            justify=tk.LEFT,
        ).grid(row=0, column=0, sticky="ew")

        tk.Label(
            panel,
            text="Escolha se a navegacao usa setas ou WASD, como em jogos.",
            font=FONTS["caption"],
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            anchor="w",
            justify=tk.LEFT,
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
            justify=tk.LEFT,
            anchor="w",
            font=FONTS["body"],
            padx=SPACING["md"],
            pady=SPACING["xs"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            wraplength=560,
        )
        self._apply_button_theme(
            button,
            bg=COLORS["panel_alt"],
            active_bg=COLORS["neutral_active"],
            fg=COLORS["text"],
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

    # ── Status strip (bottom) ──────────────────────────────────────

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

    # ── Body: sidebar + canvas ────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self.window, bg=COLORS["bg"])
        body.pack(fill=tk.BOTH, expand=True)

        sidebar_frame = tk.Frame(
            body,
            width=SIZES["sidebar_w"],
            bg=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1, bd=0,
        )
        sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        sidebar_frame.pack_propagate(False)
        self._build_sidebar(sidebar_frame)

        canvas_area = tk.Frame(body, bg=COLORS["canvas_bg"])
        canvas_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_canvas_area(canvas_area)

    # ── Sidebar ────────────────────────────────────────────────────

    def _build_sidebar(self, container):
        scroll = ScrollableFrame(container, bg=COLORS["panel"])
        scroll.pack(fill=tk.BOTH, expand=True)
        s = scroll.content
        p = {"padx": SPACING["sm"], "pady": SPACING["xs"]}

        # Section: Anotação
        self._sb_section(s, "Anotação")

        self.accept_button = self._sb_btn(s, "Validar  (Enter)", self.on_accept, state=tk.DISABLED)
        self._apply_button_theme(self.accept_button, bg=COLORS["primary"], active_bg=COLORS["primary_active"])
        self.accept_button.pack(fill=tk.X, **p)

        self.reject_button = self._sb_btn(s, "Rejeitar  (Espaço)", self.on_reject, state=tk.DISABLED)
        self._apply_button_theme(self.reject_button, bg=COLORS["danger"], active_bg=COLORS["danger_active"])
        self.reject_button.pack(fill=tk.X, **p)

        self._sb_divider(s)

        self.annotation_button = self._sb_btn(
            s, "Anotação manual  OFF  (K)", self.toggle_annotation_mode, state=tk.DISABLED,
        )
        self._apply_button_theme(
            self.annotation_button,
            bg=COLORS["accent"], active_bg=COLORS["accent_active"], fg=COLORS["text"],
        )
        self.annotation_button.pack(fill=tk.X, **p)

        self.remove_button = self._sb_btn(s, "Remover anotação  OFF", self.toggle_remove_mode, state=tk.DISABLED)
        self._apply_button_theme(self.remove_button, bg=COLORS["danger"], active_bg=COLORS["danger_active"])
        self.remove_button.pack(fill=tk.X, **p)

        self.selection_button = self._sb_btn(
            s, "Selecionar anotação  OFF  (S)", self.toggle_selection_mode, state=tk.DISABLED,
        )
        self._apply_button_theme(
            self.selection_button,
            bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self.selection_button.pack(fill=tk.X, **p)

        self.pan_button = self._sb_btn(
            s, "Mover imagem  OFF  (H)", self.toggle_pan_mode, state=tk.DISABLED,
        )
        self._apply_button_theme(
            self.pan_button,
            bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self.pan_button.pack(fill=tk.X, **p)

        self.edit_id_button = self._sb_btn(
            s, "Editar ID  OFF  (E)", self.toggle_edit_id_mode, state=tk.DISABLED,
        )
        self._apply_button_theme(
            self.edit_id_button,
            bg=COLORS["accent"], active_bg=COLORS["accent_active"], fg=COLORS["text"],
        )
        self.edit_id_button.pack(fill=tk.X, **p)

        self._sb_divider(s)

        self.roi_button = self._sb_btn(s, "Redefinir ROI  (R)", self.reset_roi)
        self._apply_button_theme(
            self.roi_button, bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self.roi_button.pack(fill=tk.X, **p)

        self.undo_button = self._sb_btn(s, "Desfazer  (Ctrl+Z)", self.undo_last_action)
        self._apply_button_theme(
            self.undo_button, bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self.undo_button.pack(fill=tk.X, **p)

        self._sb_divider(s)

        nav = tk.Frame(s, bg=COLORS["panel"])
        nav.pack(fill=tk.X, **p)
        self.prev_button = self._sb_btn(nav, "← Anterior", self.on_prev_saved)
        self._apply_button_theme(
            self.prev_button, bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self.prev_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self.next_button = self._sb_btn(nav, "Próximo →", self.on_next_saved)
        self._apply_button_theme(
            self.next_button, bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self.next_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        # Section: ID Manual
        self._sb_section(s, "ID Manual")
        entry_opts = self._entry_opts()
        self.manual_id_label = tk.Label(
            s, text="ID:", font=FONTS["label"],
            bg=COLORS["panel"], fg=COLORS["text"],
            anchor="w", padx=SPACING["sm"],
        )
        self.manual_id_label.pack(fill=tk.X, padx=SPACING["sm"], pady=(0, 2))
        self.manual_id_entry = tk.Entry(s, textvariable=self.manual_id_var, **entry_opts)
        self.manual_id_entry.pack(fill=tk.X, padx=SPACING["sm"], pady=(0, SPACING["xs"]))
        self.apply_id_button = self._sb_btn(
            s, "Aplicar ID", self.apply_manual_id_to_selection, state=tk.DISABLED,
        )
        self._apply_button_theme(self.apply_id_button, bg=COLORS["primary"], active_bg=COLORS["primary_active"])
        self.apply_id_button.pack(fill=tk.X, **p)

        if not self.tracking_enabled:
            self.manual_id_entry.config(state=tk.DISABLED)
            self.apply_id_button.config(state=tk.DISABLED)
            self.edit_id_button.config(state=tk.DISABLED)

        # Section: Classes
        self._sb_section(s, "Classes")
        self.classes_panel = tk.Frame(s, bg=COLORS["panel"])
        self.classes_panel.pack(fill=tk.X, padx=SPACING["sm"], pady=SPACING["xs"])
        self.update_class_panel()

        # Section: Exportar
        self._sb_section(s, "Exportar")
        self.save_yaml_button = self._sb_btn(s, "Salvar .yaml", self.on_save_yaml, state=tk.DISABLED)
        self._apply_button_theme(self.save_yaml_button, bg=COLORS["primary"], active_bg=COLORS["primary_active"])
        self.save_yaml_button.pack(fill=tk.X, **p)

        self.save_coco_button = self._sb_btn(s, "Salvar .coco.json", self.on_save_coco_json, state=tk.DISABLED)
        self._apply_button_theme(self.save_coco_button, bg=COLORS["primary"], active_bg=COLORS["primary_active"])
        self.save_coco_button.pack(fill=tk.X, **p)

        self.export_dataset_button = self._sb_btn(
            s, "Exportar dataset", self.on_export_dataset, state=tk.DISABLED,
        )
        self._apply_button_theme(
            self.export_dataset_button,
            bg=COLORS["accent"],
            active_bg=COLORS["accent_active"],
            fg=COLORS["text"],
        )
        self.export_dataset_button.pack(fill=tk.X, **p)

        self._sb_divider(s)

        self.quit_button = self._sb_btn(s, "Sair  (Esc)", self.on_quit)
        self._apply_button_theme(
            self.quit_button, bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self.quit_button.pack(fill=tk.X, **p)

        tk.Frame(s, bg=COLORS["panel"], height=SPACING["lg"]).pack()

    def _sb_section(self, parent, title: str):
        tk.Label(
            parent, text=title.upper(),
            font=FONTS["caption"],
            bg=COLORS["panel"], fg=COLORS["muted"],
            anchor="w", padx=SPACING["sm"], pady=2,
        ).pack(fill=tk.X, padx=SPACING["sm"], pady=(SPACING["md"], SPACING["xs"]))

    def _sb_divider(self, parent):
        tk.Frame(parent, height=1, bg=COLORS["border"]).pack(
            fill=tk.X, padx=SPACING["sm"], pady=SPACING["xs"],
        )

    def _sb_btn(self, parent, text: str, command, *, state=tk.NORMAL):
        return tk.Button(
            parent, text=text, command=command,
            font=FONTS["button"],
            padx=SIZES["btn_pad_x"], pady=SIZES["btn_pad_y"],
            bd=0, relief=tk.FLAT, cursor="hand2",
            highlightthickness=0, state=state, anchor="w",
        )

    def _entry_opts(self) -> dict:
        return {
            "font": FONTS["body"],
            "bg": COLORS["input_bg"], "fg": COLORS["text"],
            "insertbackground": COLORS["text"],
            "relief": tk.FLAT,
            "highlightthickness": 1,
            "highlightbackground": COLORS["border"],
            "highlightcolor": COLORS["accent"],
            "bd": SIZES["input_pad"],
        }

    # ── Canvas area ────────────────────────────────────────────────

    def _build_canvas_area(self, parent):
        # Aliases used by display_canvas.py for available-size measurement
        self.canvas_frame = parent
        self.canvas_shell = parent
        self.canvas_card  = parent

        self.canvas = tk.Canvas(parent, bg=COLORS["canvas_bg"], highlightthickness=0)
        self.canvas.pack(expand=True, anchor=tk.CENTER)
        self._bind_canvas_events()

    # ── Kept for compatibility with external callers ───────────────

    @staticmethod
    def _button_options(width: int, state=tk.NORMAL) -> dict:
        return {
            "width": width, "state": state,
            "font": FONTS["button"],
            "padx": SIZES["btn_pad_x"], "pady": SIZES["btn_pad_y"],
            "bd": 0, "relief": tk.FLAT, "cursor": "hand2",
            "highlightthickness": 0,
        }

    def _apply_button_theme(self, button: tk.Button, *, bg: str, active_bg: str, fg: str = "#fffaf2"):
        button.configure(
            bg=bg, fg=fg,
            activebackground=active_bg, activeforeground=fg,
            disabledforeground=COLORS["disabled_fg"],
        )
