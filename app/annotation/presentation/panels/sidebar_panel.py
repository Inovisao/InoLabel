from app.annotation.shared import *
from app.ui.components import hsep, make_btn, make_entry, section_label
from app.ui.layout.scrollable_frame import ScrollableFrame
from app.ui.theme.tokens import COLORS, SIZES, SPACING


class SidebarPanelMixin:
    def _build_body(self):
        self.body_frame = tk.Frame(self.window, bg=COLORS["bg"])
        self.body_frame.pack(fill=tk.BOTH, expand=True)

        sidebar_frame = tk.Frame(
            self.body_frame,
            width=SIZES["sidebar_w"],
            bg=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
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

        # ── Section: Annotation ───────────────────────────────────
        section_label(s, "Anotação").pack(fill=tk.X, **p)
        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=(0, SPACING["sm"]))

        self.accept_button = make_btn(s, "Validar  (Enter)", self.on_accept, variant="primary", anchor="w", state=tk.DISABLED)
        self.accept_button.pack(fill=tk.X, **p)

        self.reject_button = make_btn(s, "Rejeitar  (Espaço)", self.on_reject, variant="danger", anchor="w", state=tk.DISABLED)
        self.reject_button.pack(fill=tk.X, **p)

        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=SPACING["xs"])

        self.annotation_button = make_btn(
            s, "Anotação manual  OFF  (K)", self.toggle_annotation_mode, variant="accent", anchor="w", state=tk.DISABLED,
        )
        self.annotation_button.pack(fill=tk.X, **p)

        self.remove_button = make_btn(s, "Remover anotação  OFF", self.toggle_remove_mode, variant="danger", anchor="w", state=tk.DISABLED)
        self.remove_button.pack(fill=tk.X, **p)

        self.selection_button = make_btn(
            s, "Selecionar anotação  OFF  (S)", self.toggle_selection_mode, variant="neutral", anchor="w", state=tk.DISABLED,
        )
        self.selection_button.pack(fill=tk.X, **p)

        self.pan_button = make_btn(s, "Mover imagem  OFF  (H)", self.toggle_pan_mode, variant="neutral", anchor="w", state=tk.DISABLED)
        self.pan_button.pack(fill=tk.X, **p)

        self.edit_id_button = make_btn(s, "Editar ID  OFF  (E)", self.toggle_edit_id_mode, variant="accent", anchor="w", state=tk.DISABLED)
        self.edit_id_button.pack(fill=tk.X, **p)

        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=SPACING["xs"])

        self.roi_button = make_btn(s, "Redefinir ROI  (R)", self.reset_roi, variant="neutral", anchor="w")
        self.roi_button.pack(fill=tk.X, **p)

        self.undo_button = make_btn(s, "Desfazer  (Ctrl+Z)", self.undo_last_action, variant="neutral", anchor="w")
        self.undo_button.pack(fill=tk.X, **p)

        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=SPACING["xs"])

        rot = tk.Frame(s, bg=COLORS["panel"])
        rot.pack(fill=tk.X, **p)
        make_btn(rot, "↺ Girar", self.rotate_frame_ccw, variant="neutral").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        make_btn(rot, "Girar ↻", self.rotate_frame_cw, variant="neutral").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=SPACING["xs"])

        nav = tk.Frame(s, bg=COLORS["panel"])
        nav.pack(fill=tk.X, **p)
        self.prev_button = make_btn(nav, "← Anterior", self.on_prev_saved, variant="neutral")
        self.prev_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self.next_button = make_btn(nav, "Próximo →", self.on_next_saved, variant="neutral")
        self.next_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        # ── Section: Manual ID ────────────────────────────────────
        section_label(s, "ID Manual").pack(fill=tk.X, padx=SPACING["sm"], pady=(SPACING["lg"], SPACING["xs"]))
        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=(0, SPACING["sm"]))

        tk.Label(
            s, text="ID:",
            bg=COLORS["panel"], fg=COLORS["muted"],
            font=("Helvetica", 10),
            anchor="w", padx=SPACING["sm"],
        ).pack(fill=tk.X, padx=SPACING["sm"])

        self.manual_id_entry = make_entry(s, self.manual_id_var)
        self.manual_id_entry.pack(fill=tk.X, padx=SPACING["sm"], pady=(2, SPACING["xs"]))

        self.apply_id_button = make_btn(s, "Aplicar ID", self.apply_manual_id_to_selection, variant="primary", anchor="w", state=tk.DISABLED)
        self.apply_id_button.pack(fill=tk.X, **p)

        if not self.tracking_enabled:
            self.manual_id_entry.config(state=tk.DISABLED)
            self.apply_id_button.config(state=tk.DISABLED)
            self.edit_id_button.config(state=tk.DISABLED)

        # ── Section: Classes ──────────────────────────────────────
        section_label(s, "Classes").pack(fill=tk.X, padx=SPACING["sm"], pady=(SPACING["lg"], SPACING["xs"]))
        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=(0, SPACING["sm"]))

        self.classes_panel = tk.Frame(s, bg=COLORS["panel"])
        self.classes_panel.pack(fill=tk.X, padx=SPACING["sm"], pady=SPACING["xs"])
        self.update_class_panel()

        # ── Section: Export ───────────────────────────────────────
        section_label(s, "Exportar").pack(fill=tk.X, padx=SPACING["sm"], pady=(SPACING["lg"], SPACING["xs"]))
        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=(0, SPACING["sm"]))

        self.export_dataset_button = make_btn(s, "Exportar dataset", self.on_export_dataset, variant="accent", anchor="w", state=tk.DISABLED)
        self.export_dataset_button.pack(fill=tk.X, **p)

        hsep(s).pack(fill=tk.X, padx=SPACING["sm"], pady=SPACING["md"])

        self.quit_button = make_btn(s, "Sair  (Esc)", self.on_quit, variant="neutral", anchor="w")
        self.quit_button.pack(fill=tk.X, **p)

        tk.Frame(s, bg=COLORS["panel"], height=SPACING["lg"]).pack()
