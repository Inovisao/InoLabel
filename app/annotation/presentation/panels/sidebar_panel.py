from app.annotation.shared import *
from app.annotation.presentation.labels import SIDEBAR_LABELS, default_key, format_label
from app.ui.components import Card, make_btn, make_entry, make_toggle, section_label, sync_toggle
from app.ui.layout.scrollable_frame import ScrollableFrame
from app.ui.theme.tokens import COLORS, FONTS, SIZES, SPACING


class SidebarPanelMixin:
    # Subclasses (ex.: keypoint) trocam rotulos de botoes reaproveitados.
    sidebar_label_overrides: dict = {}

    def _build_body(self):
        self.body_frame = tk.Frame(self.window, bg=COLORS["bg"])
        self.body_frame.pack(fill=tk.BOTH, expand=True)

        sidebar_frame = tk.Frame(
            self.body_frame,
            width=SIZES["sidebar_w"],
            bg=COLORS["bg"],
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

    # ── rotulos ───────────────────────────────────────────────────

    def _sidebar_label(self, name: str):
        return self.sidebar_label_overrides.get(name) or SIDEBAR_LABELS[name]

    def _key_for_action(self, action_id) -> str:
        if not action_id:
            return ""
        service = getattr(self, "_keybind_service", None)
        if service is not None:
            return service.get_active_profile().get_key(action_id) or ""
        return default_key(action_id)

    def sidebar_text(self, name: str) -> str:
        label = self._sidebar_label(name)
        return format_label(label, self._key_for_action(label.action_id))

    def refresh_sidebar_labels(self):
        """Reaplica os rotulos (ex.: depois de remapear atalhos)."""
        for name in SIDEBAR_LABELS:
            widget = getattr(self, name, None)
            if widget is None:
                continue
            text = self.sidebar_text(name)
            try:
                if str(widget.cget("text")) != text:
                    widget.config(text=text)
            except tk.TclError:
                pass

    def sync_tool_toggle(self, name: str, active: bool):
        widget = getattr(self, name, None)
        if widget is not None:
            sync_toggle(widget, active)

    # ── construcao ────────────────────────────────────────────────

    def _sidebar_section(self, parent, title: str, *, first: bool = False) -> Card:
        top = SPACING["sm"] if first else SPACING["md"]
        section_label(parent, title).pack(fill=tk.X, padx=SPACING["sm"], pady=(top, SPACING["xs"]))
        card = Card(parent, padx=SPACING["sm"], pady=SPACING["sm"])
        card.pack(fill=tk.X, padx=SPACING["sm"])
        return card

    @staticmethod
    def _pair_row(parent) -> tk.Frame:
        row = tk.Frame(parent, bg=COLORS["panel"])
        row.pack(fill=tk.X, pady=(SPACING["xs"], 0))
        row.columnconfigure(0, weight=1, uniform="pair")
        row.columnconfigure(1, weight=1, uniform="pair")
        return row

    def _build_sidebar(self, container):
        scroll = ScrollableFrame(container, bg=COLORS["bg"])
        scroll.pack(fill=tk.BOTH, expand=True)
        s = scroll.content
        gap = {"pady": (0, SPACING["xs"])}

        # ── Decisao: a acao principal de cada frame ──────────────
        card = self._sidebar_section(s, "Decisão", first=True)
        self.accept_button = make_btn(card, self.sidebar_text("accept_button"), self.on_accept, variant="primary", state=tk.DISABLED)
        self.accept_button.pack(fill=tk.X, **gap)
        self.reject_button = make_btn(card, self.sidebar_text("reject_button"), self.on_reject, variant="danger_outline", state=tk.DISABLED)
        self.reject_button.pack(fill=tk.X)

        # ── Ferramentas: modos exclusivos, estado visivel ────────
        # Coluna unica: "Selecionar  ·  S" nao cabe em meia largura da sidebar.
        card = self._sidebar_section(s, "Ferramentas")
        tools = (
            ("annotation_button", self.toggle_annotation_mode),
            ("selection_button", self.toggle_selection_mode),
            ("remove_button", self.toggle_remove_mode),
            ("pan_button", self.toggle_pan_mode),
            ("edit_id_button", self.toggle_edit_id_mode),
        )
        for idx, (name, command) in enumerate(tools):
            toggle = make_toggle(card, self.sidebar_text(name), command, state=tk.DISABLED)
            toggle.pack(fill=tk.X, pady=(0, 0 if idx == len(tools) - 1 else SPACING["xs"]))
            setattr(self, name, toggle)

        # ── Vista e navegacao ────────────────────────────────────
        card = self._sidebar_section(s, "Vista")
        self.roi_button = make_btn(card, self.sidebar_text("roi_button"), self.reset_roi, variant="neutral")
        self.roi_button.pack(fill=tk.X, **gap)
        self.undo_button = make_btn(card, self.sidebar_text("undo_button"), self.undo_last_action, variant="neutral")
        self.undo_button.pack(fill=tk.X)

        rot = self._pair_row(card)
        make_btn(rot, "↺ Girar", self.rotate_frame_ccw, variant="neutral").grid(row=0, column=0, sticky="ew", padx=(0, 2))
        make_btn(rot, "Girar ↻", self.rotate_frame_cw, variant="neutral").grid(row=0, column=1, sticky="ew", padx=(2, 0))

        nav = self._pair_row(card)
        self.prev_button = make_btn(nav, "← Anterior", self.on_prev_saved, variant="neutral")
        self.prev_button.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self.next_button = make_btn(nav, "Próximo →", self.on_next_saved, variant="neutral")
        self.next_button.grid(row=0, column=1, sticky="ew", padx=(2, 0))

        # ── ID manual (tracking) ─────────────────────────────────
        card = self._sidebar_section(s, "ID manual")
        tk.Label(
            card, text="ID da caixa selecionada",
            bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["hint"], anchor="w",
        ).pack(fill=tk.X)
        self.manual_id_entry = make_entry(card, self.manual_id_var)
        self.manual_id_entry.pack(fill=tk.X, pady=(2, SPACING["xs"]))
        self.apply_id_button = make_btn(card, "Aplicar ID", self.apply_manual_id_to_selection, variant="primary", state=tk.DISABLED)
        self.apply_id_button.pack(fill=tk.X)

        if not self.tracking_enabled:
            self.manual_id_entry.config(state=tk.DISABLED)
            self.apply_id_button.config(state=tk.DISABLED)
            self.edit_id_button.config(state=tk.DISABLED)

        # ── Classes ──────────────────────────────────────────────
        card = self._sidebar_section(s, "Classes")
        self.classes_panel = tk.Frame(card, bg=COLORS["panel"])
        self.classes_panel.pack(fill=tk.X)
        self.update_class_panel()

        # ── Exportar ─────────────────────────────────────────────
        card = self._sidebar_section(s, "Exportar")
        self.export_dataset_button = make_btn(card, "Exportar dataset", self.on_export_dataset, variant="accent", state=tk.DISABLED)
        self.export_dataset_button.pack(fill=tk.X)

        # ── Rodape ───────────────────────────────────────────────
        self.quit_button = make_btn(s, self.sidebar_text("quit_button"), self.on_quit, variant="ghost")
        self.quit_button.pack(fill=tk.X, padx=SPACING["sm"], pady=(SPACING["md"], SPACING["lg"]))
