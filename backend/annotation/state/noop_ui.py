"""Stubs de UI para o backend — absorve chamadas que em Flet/Tkinter atualizavam widgets."""


class NoopVar:
    """Substituto de StringVar/FletVar — guarda o valor mas nao atualiza nenhuma UI."""

    def __init__(self, default: str = "") -> None:
        self._value = default

    def get(self) -> str:
        return self._value

    def set(self, value) -> None:
        self._value = str(value)


class NoopUIMixin:
    """
    Mixin que silencia todos os métodos de atualização de UI.

    Deve aparecer ANTES dos mixins de domínio no MRO para que seus
    métodos sejam encontrados antes das implementações Flet/Tkinter.
    """

    def _init_noop_vars(self) -> None:
        self.info_var = NoopVar()
        self.manual_id_var = NoopVar()
        self.image_name_var = NoopVar()
        self.target_classes_var = None
        self.drawing_rect_id = None

    # ── Display / render ──────────────────────────────────────────────────────

    def update_display(self, *, refresh_status: bool = False) -> None:
        pass

    # ── Status bar ────────────────────────────────────────────────────────────

    def update_status(self) -> None:
        pass

    def update_status_blocks(self) -> None:
        pass

    def update_image_info(self) -> None:
        pass

    # ── Buttons / panel ───────────────────────────────────────────────────────

    def update_class_panel(self, **_kwargs) -> None:
        pass

    def update_annotation_button(self) -> None:
        pass

    def update_remove_button(self) -> None:
        pass

    def update_selection_button(self) -> None:
        pass

    def update_edit_id_button(self) -> None:
        pass

    def update_pan_button(self) -> None:
        pass

    def update_key_mapping_button(self) -> None:
        pass

    def _redraw_class_buttons(self) -> None:
        pass

    def enable_controls_after_roi(self) -> None:
        pass

    def disable_controls_for_roi(self) -> None:
        pass

    # ── Canvas overlays (noop no backend) ─────────────────────────────────────

    def _draw_active_manual_rectangle(self) -> None:
        pass

    def _draw_roi_overlay_on_canvas(self) -> None:
        pass
