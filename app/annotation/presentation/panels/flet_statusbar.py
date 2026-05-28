"""Flet: statusbar inferior — blocos de estado estruturado."""

from __future__ import annotations

import flet as ft

from app.ui.components.flet_components import FletVar, ghost_btn, icon_btn
from app.ui.theme.flet_theme import COLORS, FONT, SIZES, SPACING


class _StatusBlock(ft.Container):
    def __init__(self, initial: str = "", color: str = COLORS["muted"]):
        self.txt = ft.Text(initial, size=FONT["caption"], color=color, no_wrap=True)
        super().__init__(
            content=self.txt,
            padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=0),
            border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])),
        )

    def update_text(self, value: str, color: str | None = None):
        self.txt.value = value
        if color is not None:
            self.txt.color = color


class FletStatusbarPanelMixin:
    def _build_flet_statusbar(self):
        self._sb_source = _StatusBlock("—")
        self._sb_roi    = _StatusBlock("ROI 0/4 pts")
        self._sb_mode   = _StatusBlock("Validação")
        self._sb_class  = _StatusBlock("—")
        self._sb_sel    = _StatusBlock("")

        # Vars compatíveis com DisplayStatusMixin
        self.status_source_var = FletVar(self._sb_source.txt)
        self.status_roi_var    = FletVar(self._sb_roi.txt)
        self.status_mode_var   = FletVar(self._sb_mode.txt)
        self.status_class_var  = FletVar(self._sb_class.txt)
        self.status_sel_var    = FletVar(self._sb_sel.txt)

        # Referências de label para _config_if_changed
        self.status_roi_lbl    = self._sb_roi.txt
        self.status_mode_lbl   = self._sb_mode.txt
        self.status_class_lbl  = self._sb_class.txt
        self.status_sel_lbl    = self._sb_sel.txt

        self.open_folder_button = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            icon_size=16,
            icon_color=COLORS["muted"],
            on_click=lambda _: self.on_open_in_folder() if hasattr(self, "on_open_in_folder") else None,
            tooltip="Abrir no Explorer",
            disabled=True,
            style=ft.ButtonStyle(padding=4),
        )
        self.delete_image_button = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_size=16,
            icon_color=COLORS["danger"],
            on_click=lambda _: self._on_delete_image() if hasattr(self, "_on_delete_image") else None,
            tooltip="Remover imagem",
            disabled=True,
            style=ft.ButtonStyle(padding=4),
        )

        self._flet_statusbar = ft.Container(
            content=ft.Row(
                controls=[
                    self._sb_source,
                    self._sb_roi,
                    self._sb_mode,
                    self._sb_class,
                    self._sb_sel,
                    ft.Container(expand=True),
                    self._image_name_text,
                    ft.Container(width=4),
                    self.open_folder_button,
                    self.delete_image_button,
                    ft.Container(width=SPACING["sm"]),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            bgcolor=COLORS["surface"],
            border=ft.border.only(top=ft.BorderSide(1, COLORS["border"])),
            height=SIZES["statusbar_h"],
        )
