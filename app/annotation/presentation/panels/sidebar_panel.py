from app.annotation.shared import *
from app.ui.layout.scrollable_frame import ScrollableFrame
from app.ui.theme import COLORS, FONTS, SIZES, SPACING


class SidebarPanelMixin:
    def _build_body(self):
        self.body_frame = tk.Frame(self.window, bg=COLORS["bg"])
        self.body_frame.pack(fill=tk.BOTH, expand=True)

        sidebar_frame = tk.Frame(
            self.body_frame,
            width=SIZES["sidebar_w"],
            bg=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1, bd=0,
        )
        sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        sidebar_frame.pack_propagate(False)
        self._build_sidebar(sidebar_frame)

        self.main_content_area = tk.Frame(self.body_frame, bg=COLORS["canvas_bg"])
        self.main_content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.show_annotation_screen()

    def _clear_main_content(self):
        for child in self.main_content_area.winfo_children():
            child.destroy()

    def show_annotation_screen(self):
        self._clear_main_content()
        self.export_screen_active = False
        self._build_canvas_area(self.main_content_area)
        if self.current_frame is not None:
            self.update_display(refresh_status=True)

    def _build_sidebar(self, container):
        scroll = ScrollableFrame(container, bg=COLORS["panel"])
        scroll.pack(fill=tk.BOTH, expand=True)
        s = scroll.content
        p = {"padx": SPACING["sm"], "pady": SPACING["xs"]}

        # ── Seção: Anotação ────────────────────────────────────────
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

        # ── Seção: ID Manual ───────────────────────────────────────
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

        # ── Seção: Classes ─────────────────────────────────────────
        self._sb_section(s, "Classes")
        self.classes_panel = tk.Frame(s, bg=COLORS["panel"])
        self.classes_panel.pack(fill=tk.X, padx=SPACING["sm"], pady=SPACING["xs"])
        self.update_class_panel()

        # ── Seção: Exportar ────────────────────────────────────────
        self._sb_section(s, "Exportar")
        self.export_dataset_button = self._sb_btn(
            s, "Exportar dataset", self.on_export_dataset, state=tk.DISABLED,
        )
        self._apply_button_theme(
            self.export_dataset_button,
            bg=COLORS["accent"], active_bg=COLORS["accent_active"], fg=COLORS["text"],
        )
        self.export_dataset_button.pack(fill=tk.X, **p)

        self._sb_divider(s)

        self.quit_button = self._sb_btn(s, "Sair  (Esc)", self.on_quit)
        self._apply_button_theme(
            self.quit_button, bg=COLORS["neutral"], active_bg=COLORS["neutral_active"], fg=COLORS["text"],
        )
        self.quit_button.pack(fill=tk.X, **p)

        tk.Frame(s, bg=COLORS["panel"], height=SPACING["lg"]).pack()

    # ── helpers de construção ──────────────────────────────────────

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
