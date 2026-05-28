"""Flet: painel do canvas — Stack com imagem + overlay de desenho."""

from __future__ import annotations

import flet as ft

from app.ui.theme.flet_theme import COLORS, SPACING


class FletCanvasPanelMixin:
    def _build_flet_body(self):
        self._build_flet_sidebar()
        self._flet_canvas_area = ft.Container(
            content=self._build_flet_canvas_container(),
            expand=True,
            bgcolor=COLORS["canvas_bg"],
        )

    def _build_flet_canvas_container(self) -> ft.Control:
        # Imagem do frame atual
        self._flet_canvas_image = ft.Image(
            src_base64="",
            fit=ft.ImageFit.NONE,
            width=1,
            height=1,
        )
        # Container posicionável que contém a imagem
        self._flet_image_wrapper = ft.Container(
            content=self._flet_canvas_image,
            left=0,
            top=0,
        )
        # Overlay para o retângulo de anotação manual
        self._flet_drawing_rect = ft.Container(
            visible=False,
            border=ft.border.all(2, ft.Colors.YELLOW),
            left=0, top=0, width=0, height=0,
        )

        self._flet_canvas_stack = ft.Stack(
            controls=[
                self._flet_image_wrapper,
                self._flet_drawing_rect,
            ],
            width=400,
            height=300,
        )

        # GestureDetector captura todos os eventos de mouse
        self._flet_gesture = ft.GestureDetector(
            content=ft.Container(
                content=self._flet_canvas_stack,
                alignment=ft.alignment.center,
            ),
            on_tap_down=self._on_flet_mouse_down,
            on_pan_update=self._on_flet_mouse_drag,
            on_tap_up=self._on_flet_mouse_up,
            on_secondary_tap_down=self._on_flet_secondary_down,
            on_secondary_tap_up=self._on_flet_pan_end,
            on_scroll=self._on_flet_scroll,
            mouse_cursor=ft.MouseCursor.PRECISE,
        )

        # Canvas = GestureDetector centralizado
        self._flet_canvas_container = ft.Container(
            content=self._flet_gesture,
            expand=True,
            bgcolor=COLORS["canvas_bg"],
            alignment=ft.alignment.center,
        )

        # Armazena dimensão para _canvas_viewport_limits
        self._canvas_w: int = 800
        self._canvas_h: int = 600

        return self._flet_canvas_container

    def _bind_canvas_events(self):
        pass  # eventos já registrados no GestureDetector

    def show_annotation_screen(self):
        self._flet_canvas_area.content = self._build_flet_canvas_container()
        if self.current_frame is not None:
            self.update_display(refresh_status=True)
        self.page.update()
