"""Flet: sidebar — controles de anotação, classes, exportar, navegação."""

from __future__ import annotations

from typing import List

import flet as ft

from app.ui.components.flet_components import (
    FletVar, accent_btn, caption_text, danger_btn, ghost_btn,
    hdivider, label_text, neutral_btn, primary_btn, section_header, text_field,
)
from app.ui.theme.flet_theme import COLORS, FONT, SIZES, SPACING
from app.ui.theme.palette import CLASS_COLORS


class FletSidebarPanelMixin:
    def _build_flet_sidebar(self):
        self._flet_sidebar = ft.Container(
            content=ft.Column(
                controls=[self._sidebar_scroll()],
                expand=True,
                spacing=0,
            ),
            width=SIZES["sidebar_w"],
            bgcolor=COLORS["surface"],
            border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])),
        )

    def _sidebar_scroll(self) -> ft.Control:
        return ft.ListView(
            controls=self._sidebar_sections(),
            expand=True,
            spacing=0,
            padding=ft.padding.all(SPACING["sm"]),
        )

    def _sidebar_sections(self) -> list[ft.Control]:
        return [
            self._section_annotation(),
            self._section_manual_id(),
            self._section_classes(),
            self._section_export(),
            self._section_navigation(),
            self._section_quit(),
        ]

    # ── Seção: Anotação ────────────────────────────────────────────────────────

    def _section_annotation(self) -> ft.Control:
        self.accept_button = primary_btn(
            "Validar  (Enter)",
            lambda _: self.on_accept() if hasattr(self, "on_accept") else None,
            disabled=True,
        )
        self.reject_button = danger_btn(
            "Rejeitar  (Espaço)",
            lambda _: self.on_reject() if hasattr(self, "on_reject") else None,
            disabled=True,
        )
        self.annotation_button = accent_btn(
            "Anotação manual  OFF  (K)",
            lambda _: self.toggle_annotation_mode() if hasattr(self, "toggle_annotation_mode") else None,
            disabled=True,
        )
        self.remove_button = danger_btn(
            "Remover anotação  OFF",
            lambda _: self.toggle_remove_mode() if hasattr(self, "toggle_remove_mode") else None,
            disabled=True,
        )
        self.selection_button = neutral_btn(
            "Selecionar anotação  OFF  (S)",
            lambda _: self.toggle_selection_mode() if hasattr(self, "toggle_selection_mode") else None,
            disabled=True,
        )
        self.pan_button = neutral_btn(
            "Mover imagem  OFF  (H)",
            lambda _: self.toggle_pan_mode() if hasattr(self, "toggle_pan_mode") else None,
            disabled=True,
        )
        self.edit_id_button = accent_btn(
            "Editar ID  OFF  (E)",
            lambda _: self.toggle_edit_id_mode() if hasattr(self, "toggle_edit_id_mode") else None,
            disabled=True,
        )
        self.roi_button = neutral_btn(
            "Redefinir ROI  (R)",
            lambda _: self.reset_roi() if hasattr(self, "reset_roi") else None,
            disabled=False,
        )

        return ft.Column(
            controls=[
                section_header("ANOTAÇÃO"),
                ft.Container(height=SPACING["xs"]),
                self.accept_button,
                ft.Container(height=SPACING["xs"]),
                self.reject_button,
                hdivider(),
                self.annotation_button,
                ft.Container(height=SPACING["xs"]),
                self.remove_button,
                ft.Container(height=SPACING["xs"]),
                self.selection_button,
                ft.Container(height=SPACING["xs"]),
                self.pan_button,
                ft.Container(height=SPACING["xs"]),
                self.edit_id_button,
                hdivider(),
                self.roi_button,
                ft.Container(height=SPACING["sm"]),
            ],
            spacing=0,
        )

    # ── Seção: ID Manual ───────────────────────────────────────────────────────

    def _section_manual_id(self) -> ft.Control:
        if not getattr(self, "tracking_enabled", False):
            return ft.Container()

        self._manual_id_field = text_field(
            label="ID manual",
            value="",
            on_change=lambda e: self._on_manual_id_change(e.control.value),
        )
        self._manual_class_field = text_field(
            label="Classe",
            value=self.target_classes[0] if self.target_classes else "",
            on_change=lambda e: self._on_class_input_change(e.control.value),
        )
        self.apply_id_button = neutral_btn(
            "Aplicar ID",
            lambda _: self._apply_manual_id() if hasattr(self, "_apply_manual_id") else None,
            disabled=True,
        )

        # Proxies compatíveis com o código legado
        self._id_proxy_text = ft.Text("")
        self._class_proxy_text = ft.Text(self.target_classes[0] if self.target_classes else "")
        self.manual_id_var = FletVar(self._id_proxy_text)
        self.manual_class_var = FletVar(self._class_proxy_text)

        return ft.Column(
            controls=[
                section_header("ID MANUAL"),
                ft.Container(height=SPACING["xs"]),
                self._manual_id_field,
                ft.Container(height=SPACING["xs"]),
                self._manual_class_field,
                ft.Container(height=SPACING["xs"]),
                self.apply_id_button,
                ft.Container(height=SPACING["sm"]),
            ],
            spacing=0,
        )

    def _on_manual_id_change(self, value: str):
        if hasattr(self, "manual_id_var"):
            self.manual_id_var.set(value)

    def _on_class_input_change(self, value: str):
        if hasattr(self, "manual_class_var"):
            self.manual_class_var.set(value)

    # ── Seção: Classes ─────────────────────────────────────────────────────────

    def _section_classes(self) -> ft.Control:
        self._classes_column = ft.Column(spacing=SPACING["xs"])
        self._rebuild_class_list()

        return ft.Column(
            controls=[
                section_header("CLASSES"),
                ft.Container(height=SPACING["xs"]),
                self._classes_column,
                ft.Container(height=SPACING["sm"]),
            ],
            spacing=0,
        )

    def _rebuild_class_list(self):
        if not hasattr(self, "_classes_column"):
            return
        rows: list[ft.Control] = []
        classes = list(getattr(self, "target_classes", []))
        active = getattr(self, "_active_class_name_val", classes[0] if classes else "")
        for idx, name in enumerate(classes):
            color = CLASS_COLORS[idx % len(CLASS_COLORS)]
            is_active = name == active
            rows.append(self._class_row(idx, name, color, is_active))
        self._classes_column.controls = rows
        if hasattr(self, "page"):
            self.page.update()

    def _class_row(self, idx: int, name: str, color: str, is_active: bool) -> ft.Control:
        def activate(_e, n=name):
            if hasattr(self, "set_active_class"):
                self.set_active_class(n)
            self._active_class_name_val = n
            self._rebuild_class_list()

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(width=4, height=32, bgcolor=color,
                                 border_radius=ft.border_radius.only(top_left=SIZES["radius_sm"], bottom_left=SIZES["radius_sm"])),
                    ft.Container(width=SPACING["xs"]),
                    ft.Text(str(idx + 1), size=FONT["caption"], color=COLORS["muted"], width=18),
                    ft.Text(name, size=FONT["label"], weight=ft.FontWeight.W_500,
                            color=COLORS["primary"] if is_active else COLORS["text"], expand=True),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["primary_muted"] if is_active else COLORS["surface"],
            border=ft.border.all(1, COLORS["primary"] if is_active else COLORS["border"]),
            border_radius=SIZES["radius_sm"],
            height=34,
            on_click=activate,
            ink=True,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

    def update_class_panel(self):
        if hasattr(self, "_classes_column"):
            self._rebuild_class_list()

    # ── Seção: Exportar ────────────────────────────────────────────────────────

    def _section_export(self) -> ft.Control:
        self._export_format = ft.Dropdown(
            label="Formato",
            value="yolo_detection",
            options=[
                ft.dropdown.Option("yolo_detection", "YOLO Detection"),
                ft.dropdown.Option("yolo_obb",       "YOLO OBB"),
            ],
            height=44,
            text_size=FONT["body"],
            label_style=ft.TextStyle(size=FONT["caption"]),
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            bgcolor=COLORS["surface"],
            filled=True,
        )
        self.export_dataset_button = primary_btn(
            "Exportar dataset",
            lambda _: self._show_export_screen() if hasattr(self, "_show_export_screen") else None,
            disabled=True,
            icon=ft.Icons.UPLOAD,
        )

        return ft.Column(
            controls=[
                section_header("EXPORTAR"),
                ft.Container(height=SPACING["xs"]),
                self._export_format,
                ft.Container(height=SPACING["xs"]),
                self.export_dataset_button,
                ft.Container(height=SPACING["sm"]),
            ],
            spacing=0,
        )

    # ── Seção: Navegação ───────────────────────────────────────────────────────

    def _section_navigation(self) -> ft.Control:
        self.prev_frame_button = neutral_btn(
            "← Frame anterior",
            lambda _: self.go_to_prev_saved() if hasattr(self, "go_to_prev_saved") else None,
            disabled=True,
        )
        self.next_frame_button = neutral_btn(
            "Próximo frame →",
            lambda _: self.go_to_next_saved() if hasattr(self, "go_to_next_saved") else None,
            disabled=True,
        )

        return ft.Column(
            controls=[
                section_header("NAVEGAÇÃO"),
                ft.Container(height=SPACING["xs"]),
                self.prev_frame_button,
                ft.Container(height=SPACING["xs"]),
                self.next_frame_button,
                ft.Container(height=SPACING["sm"]),
            ],
            spacing=0,
        )

    # ── Seção: Sair ────────────────────────────────────────────────────────────

    def _section_quit(self) -> ft.Control:
        return ft.Column(
            controls=[
                hdivider(),
                ft.Container(height=SPACING["xs"]),
                danger_btn(
                    "Sair  (Esc)",
                    lambda _: self.on_quit() if hasattr(self, "on_quit") else None,
                    icon=ft.Icons.LOGOUT,
                ),
            ],
            spacing=0,
        )

    # ── Compat: métodos de update de botão ────────────────────────────────────

    def update_annotation_button(self):
        if not hasattr(self, "annotation_button"):
            return
        on = getattr(self, "annotation_mode", False)
        self.annotation_button.text = f"Anotação manual  {'ON ' if on else 'OFF'}  (K)"
        self.annotation_button.style.bgcolor[ft.ControlState.DEFAULT] = (
            COLORS["accent"] if on else COLORS["neutral"]
        )
        if hasattr(self, "page"):
            self.page.update()

    def update_remove_button(self):
        if not hasattr(self, "remove_button"):
            return
        on = getattr(self, "remove_mode", False)
        self.remove_button.text = f"Remover anotação  {'ON ' if on else 'OFF'}"
        if hasattr(self, "page"):
            self.page.update()

    def update_selection_button(self):
        if not hasattr(self, "selection_button"):
            return
        on = getattr(self, "selection_mode", False)
        self.selection_button.text = f"Selecionar anotação  {'ON ' if on else 'OFF'}  (S)"
        if hasattr(self, "page"):
            self.page.update()

    def update_edit_id_button(self):
        if not hasattr(self, "edit_id_button"):
            return
        on = getattr(self, "edit_id_mode", False)
        self.edit_id_button.text = f"Editar ID  {'ON ' if on else 'OFF'}  (E)"
        if hasattr(self, "page"):
            self.page.update()

    def update_pan_button(self):
        if not hasattr(self, "pan_button"):
            return
        on = getattr(self, "pan_mode", False)
        self.pan_button.text = f"Mover imagem  {'ON ' if on else 'OFF'}  (H)"
        if hasattr(self, "page"):
            self.page.update()
