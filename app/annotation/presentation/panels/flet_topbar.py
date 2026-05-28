"""Flet: topbar — badge de modo, info label, botões de ação."""

from __future__ import annotations

import flet as ft

from app.ui.components.flet_components import badge, ghost_btn, icon_btn
from app.ui.theme.flet_theme import COLORS, FONT, SIZES, SPACING


class FletTopbarPanelMixin:
    def _build_flet_topbar(self):
        mode_label = self.task_mode.label
        color_map = {
            "Tracking":       "primary",
            "Detection":      "accent",
            "OBB":            "danger",
            "Classification": "success",
        }
        badge_color = color_map.get(mode_label, "neutral")

        self._keybind_btn = ghost_btn(
            "Atalhos",
            lambda _: self._open_keybind_editor() if hasattr(self, "_open_keybind_editor") else None,
            icon=ft.Icons.KEYBOARD,
        )

        self._flet_topbar = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(width=SPACING["md"]),
                    badge(mode_label, badge_color),
                    ft.Container(width=SPACING["sm"]),
                    ft.Container(
                        content=self._info_text,
                        expand=True,
                    ),
                    self._keybind_btn,
                    ft.Container(width=SPACING["sm"]),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            bgcolor=COLORS["surface"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
            height=SIZES["topbar_h"],
        )
