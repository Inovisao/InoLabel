"""Toggle de ferramenta — botao com estado ligado/desligado visivel.

Antes os modos (anotar, selecionar, mover...) so trocavam "ON/OFF" no texto. O
estado agora e visual: ligado = fundo primary_soft, contorno e texto na cor primaria.
Continua sendo um tk.Button, entao config(state=...) e config(text=...) seguem valendo.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from app.ui.theme.tokens import COLORS, FONTS, SIZES, SPACING


class ToggleButton(tk.Button):
    """Botao de ferramenta com estado; use set_active() em vez de mudar cores na mao."""

    def __init__(self, parent: tk.Widget, text: str, command: Optional[Callable] = None, **kw):
        options = dict(
            text=text,
            font=FONTS["button"],
            padx=SIZES["btn_pad_x"],
            pady=SPACING["xs"] + 2,
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            highlightthickness=2,
            anchor=tk.W,
            disabledforeground=COLORS["disabled_fg"],
        )
        options.update(kw)
        if command is not None:
            options["command"] = command
        super().__init__(parent, **options)
        self._active = False
        self._hovered = False
        self._apply_style()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    @property
    def active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        active = bool(active)
        if active == self._active:
            return
        self._active = active
        self._apply_style()

    def _palette(self) -> dict:
        if self._active:
            return {
                "bg": COLORS["primary_soft"],
                "hover": COLORS["primary_soft"],
                "fg": COLORS["primary"],
                "border": COLORS["primary"],
            }
        return {
            "bg": COLORS["neutral"],
            "hover": COLORS["neutral_active"],
            "fg": COLORS["text"],
            # Desligado: contorno da mesma cor do fundo, so para nao mudar o tamanho.
            "border": COLORS["neutral"],
        }

    def _apply_style(self) -> None:
        pal = self._palette()
        enabled = str(self.cget("state")) != tk.DISABLED
        bg = pal["hover"] if (self._hovered and enabled) else pal["bg"]
        self.configure(
            bg=bg,
            fg=pal["fg"],
            activebackground=pal["hover"],
            activeforeground=pal["fg"],
            highlightbackground=pal["border"],
            highlightcolor=pal["border"],
        )

    def _on_enter(self, _event) -> None:
        self._hovered = True
        self._apply_style()

    def _on_leave(self, _event) -> None:
        self._hovered = False
        self._apply_style()


def make_toggle(
    parent: tk.Widget,
    text: str,
    command: Optional[Callable] = None,
    *,
    state: str = tk.NORMAL,
    active: bool = False,
) -> ToggleButton:
    btn = ToggleButton(parent, text, command, state=state)
    btn.set_active(active)
    return btn


def sync_toggle(widget, active: bool) -> None:
    """Aplica o estado em um ToggleButton; ignora widgets que nao sao toggles."""
    setter = getattr(widget, "set_active", None)
    if setter is not None:
        setter(active)
