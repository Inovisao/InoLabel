"""Flet: janela principal — inicializa page, tema e orquestra os painéis."""

from __future__ import annotations

import flet as ft

from app.ui.theme.flet_theme import COLORS, FONT, SIZES, SPACING
from app.ui.components.flet_components import FletVar


class FletMainWindowMixin:
    """Substitui MainWindowMixin para ambientes Flet."""

    def _build_ui(self):
        page: ft.Page = self.page

        page.title = f"InoLabel — {self.task_mode.label}"
        page.bgcolor = COLORS["bg"]
        page.padding = 0
        page.spacing = 0
        page.window.min_width = 900
        page.window.min_height = 600

        self._initialize_flet_vars()
        self._build_flet_layout()
        page.on_keyboard_event = self._on_page_keyboard_event
        page.update()

    def _initialize_flet_vars(self):
        self._info_text = ft.Text("", size=FONT["body"], color=COLORS["muted"], expand=True)
        self.info_var = FletVar(self._info_text,
                                f"{self.task_mode.label} · ROI opcional. Pressione R para definir 4 pontos.")

        self._image_name_text = ft.Text("-", size=FONT["caption"], color=COLORS["muted"])
        self.image_name_var = FletVar(self._image_name_text)

        self._mode_info_text = ft.Text("", size=FONT["caption"], color=COLORS["muted"], expand=True)
        self.mode_info_var = FletVar(self._mode_info_text)

    def _build_flet_layout(self):
        self._build_flet_topbar()
        self._build_flet_body()
        self._build_flet_statusbar()
        self.page.controls = [
            ft.Column(
                controls=[
                    self._flet_topbar,
                    ft.Row(
                        controls=[self._flet_sidebar, self._flet_canvas_area],
                        expand=True,
                        spacing=0,
                    ),
                    self._flet_statusbar,
                ],
                expand=True,
                spacing=0,
            )
        ]

    def _on_page_keyboard_event(self, e: ft.KeyboardEvent):
        if getattr(self, "_ignore_keyboard", False):
            return
        self._dispatch_keyboard(e)

    def run(self):
        pass  # Flet já está rodando via ft.app()

    def _destroy_window(self):
        try:
            self.page.window.close()
        except Exception:  # pylint: disable=broad-except
            pass

    def _schedule(self, delay_ms: int, callback) -> None:
        import threading  # pylint: disable=import-outside-toplevel
        t = threading.Timer(delay_ms / 1000.0, callback)
        t.daemon = True
        t.start()
