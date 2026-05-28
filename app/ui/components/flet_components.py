"""Primitivos Flet reutilizáveis — botões, cards, inputs, separadores."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from app.ui.theme.flet_theme import COLORS, FONT, SIZES, SPACING


# ── Var proxy ─────────────────────────────────────────────────────────────────

class FletVar:
    """Proxy que imita tk.StringVar: mantém valor e atualiza um ft.Text opcional."""

    def __init__(self, control: Optional[ft.Text] = None, value: str = ""):
        self._value = value
        self._control = control

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value
        if self._control is not None:
            self._control.value = value

    def bind(self, control: ft.Text) -> None:
        self._control = control
        control.value = self._value


# ── Botões ────────────────────────────────────────────────────────────────────

def _btn_style(bg: str, fg: str, hover_bg: str) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        color={ft.ControlState.DEFAULT: fg, ft.ControlState.DISABLED: COLORS["disabled"]},
        bgcolor={
            ft.ControlState.DEFAULT: bg,
            ft.ControlState.HOVERED: hover_bg,
            ft.ControlState.PRESSED: hover_bg,
            ft.ControlState.DISABLED: COLORS["neutral"],
        },
        shape=ft.RoundedRectangleBorder(radius=SIZES["radius_sm"]),
        padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
        overlay_color=ft.Colors.TRANSPARENT,
        animation_duration=120,
    )


def primary_btn(
    text: str,
    on_click: Optional[Callable] = None,
    *,
    disabled: bool = False,
    expand: bool = True,
    icon: Optional[str] = None,
) -> ft.ElevatedButton:
    btn = ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        expand=expand,
        style=_btn_style(COLORS["primary"], COLORS["on_primary"], COLORS["primary_hover"]),
        height=SIZES["btn_h"],
    )
    return btn


def danger_btn(
    text: str,
    on_click: Optional[Callable] = None,
    *,
    disabled: bool = False,
    expand: bool = True,
    icon: Optional[str] = None,
) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        expand=expand,
        style=_btn_style(COLORS["danger"], COLORS["on_danger"], COLORS["danger_hover"]),
        height=SIZES["btn_h"],
    )


def accent_btn(
    text: str,
    on_click: Optional[Callable] = None,
    *,
    disabled: bool = False,
    expand: bool = True,
    icon: Optional[str] = None,
) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        expand=expand,
        style=_btn_style(COLORS["accent"], COLORS["on_accent"], COLORS["accent_hover"]),
        height=SIZES["btn_h"],
    )


def neutral_btn(
    text: str,
    on_click: Optional[Callable] = None,
    *,
    disabled: bool = False,
    expand: bool = True,
    icon: Optional[str] = None,
) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        expand=expand,
        style=_btn_style(COLORS["neutral"], COLORS["on_neutral"], COLORS["neutral_hover"]),
        height=SIZES["btn_h"],
    )


def ghost_btn(
    text: str,
    on_click: Optional[Callable] = None,
    *,
    disabled: bool = False,
    expand: bool = False,
    icon: Optional[str] = None,
) -> ft.TextButton:
    return ft.TextButton(
        text=text,
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        expand=expand,
        style=ft.ButtonStyle(
            color={
                ft.ControlState.DEFAULT: COLORS["muted"],
                ft.ControlState.HOVERED: COLORS["text"],
                ft.ControlState.DISABLED: COLORS["disabled"],
            },
            shape=ft.RoundedRectangleBorder(radius=SIZES["radius_sm"]),
            padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=4),
        ),
    )


def icon_btn(
    icon: str,
    on_click: Optional[Callable] = None,
    *,
    tooltip: str = "",
    disabled: bool = False,
    color: str = COLORS["muted"],
) -> ft.IconButton:
    return ft.IconButton(
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        tooltip=tooltip,
        icon_color=color,
        icon_size=SIZES["icon"],
        style=ft.ButtonStyle(
            overlay_color={ft.ControlState.HOVERED: COLORS["surface_alt"]},
            shape=ft.RoundedRectangleBorder(radius=SIZES["radius_sm"]),
        ),
    )


# ── Cards ─────────────────────────────────────────────────────────────────────

def card(
    content: ft.Control,
    padding: int = SPACING["md"],
    expand: bool = False,
) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=COLORS["surface"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=SIZES["radius"],
        padding=padding,
        expand=expand,
    )


def surface(
    content: ft.Control,
    padding: int = SPACING["md"],
    expand: bool = False,
    bgcolor: str = COLORS["surface_alt"],
) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=bgcolor,
        border_radius=SIZES["radius_sm"],
        padding=padding,
        expand=expand,
    )


# ── Texto e separadores ───────────────────────────────────────────────────────

def section_header(text: str) -> ft.Text:
    return ft.Text(
        text,
        size=FONT["caption"],
        weight=ft.FontWeight.W_600,
        color=COLORS["muted"],
        spans=None,
    )


def label_text(text: str, color: str = COLORS["text"], size: int = FONT["label"]) -> ft.Text:
    return ft.Text(text, size=size, weight=ft.FontWeight.W_500, color=color)


def caption_text(text: str, color: str = COLORS["muted"]) -> ft.Text:
    return ft.Text(text, size=FONT["caption"], color=color)


def hdivider() -> ft.Divider:
    return ft.Divider(height=1, color=COLORS["border"], thickness=1)


# ── Badge / chip ──────────────────────────────────────────────────────────────

def badge(text: str, color: str = "primary") -> ft.Container:
    bg_map = {
        "primary": (COLORS["primary_muted"], COLORS["primary"]),
        "accent":  (COLORS["accent_muted"],  COLORS["accent"]),
        "danger":  (COLORS["danger_muted"],  COLORS["danger"]),
        "success": (COLORS["success_muted"], COLORS["success"]),
        "neutral": (COLORS["neutral"],       COLORS["muted"]),
    }
    bg, fg = bg_map.get(color, bg_map["neutral"])
    return ft.Container(
        content=ft.Text(text, size=FONT["caption"], weight=ft.FontWeight.W_600, color=fg),
        bgcolor=bg,
        border_radius=99,
        padding=ft.padding.symmetric(horizontal=10, vertical=3),
    )


# ── Input ─────────────────────────────────────────────────────────────────────

def text_field(
    label: str = "",
    value: str = "",
    on_change: Optional[Callable] = None,
    on_submit: Optional[Callable] = None,
    hint: str = "",
    width: Optional[int] = None,
    expand: bool = True,
    password: bool = False,
    autofocus: bool = False,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        hint_text=hint,
        on_change=on_change,
        on_submit=on_submit,
        width=width,
        expand=expand,
        password=password,
        autofocus=autofocus,
        height=SIZES["input_h"],
        text_size=FONT["body"],
        label_style=ft.TextStyle(size=FONT["caption"], color=COLORS["muted"]),
        border_color=COLORS["border"],
        focused_border_color=COLORS["primary"],
        bgcolor=COLORS["surface"],
        filled=True,
        fill_color=COLORS["surface"],
        content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=SIZES["radius_sm"],
        cursor_color=COLORS["primary"],
    )


# ── Classe color tag ──────────────────────────────────────────────────────────

def class_tag(index: int, name: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(width=4, height=32, bgcolor=color, border_radius=ft.border_radius.only(top_left=4, bottom_left=4)),
                ft.Text(f"{index + 1}", size=FONT["caption"], color=COLORS["muted"], width=20),
                ft.Text(name, size=FONT["label"], weight=ft.FontWeight.W_500, color=COLORS["text"], expand=True),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=COLORS["surface"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=SIZES["radius_sm"],
        height=36,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
