"""Rotulos dos botoes da sidebar — fonte unica para a construcao e para os updates.

Antes o texto inicial ("Anotação manual OFF (K)") e o de update ("Modo anotacao ON (K)")
vinham de lugares diferentes e divergiam. A tecla vem do perfil de atalhos ativo,
entao o rotulo acompanha remapeamentos.
"""

from __future__ import annotations

from typing import Dict, NamedTuple, Optional

from app.annotation.keybinds.actions import ACTION_REGISTRY


class ButtonLabel(NamedTuple):
    text: str
    action_id: Optional[str] = None   # acao remapeavel; a tecla vem do perfil ativo
    fixed_key: Optional[str] = None   # tecla fixa (nao remapeavel)


SIDEBAR_LABELS: Dict[str, ButtonLabel] = {
    "accept_button":     ButtonLabel("Validar", "accept"),
    "reject_button":     ButtonLabel("Rejeitar", "reject"),
    "annotation_button": ButtonLabel("Anotar", "toggle_draw"),
    "selection_button":  ButtonLabel("Selecionar", "toggle_selection"),
    "remove_button":     ButtonLabel("Remover", "toggle_remove"),
    "pan_button":        ButtonLabel("Mover", "toggle_pan"),
    "edit_id_button":    ButtonLabel("Editar ID", "toggle_edit_id"),
    "roi_button":        ButtonLabel("Redefinir ROI", "reset_roi"),
    "undo_button":       ButtonLabel("Desfazer", "undo"),
    "quit_button":       ButtonLabel("Sair", fixed_key="Esc"),
}

KEY_SEPARATOR = "  ·  "

_DEFAULT_KEYS = {action.id: action.default_arrows for action in ACTION_REGISTRY}


def display_key(key: str) -> str:
    from app.annotation.keybinds.keybind_editor import _display_key  # pylint: disable=import-outside-toplevel
    return _display_key(key)


def format_label(label: ButtonLabel, key: Optional[str]) -> str:
    """"Texto  ·  Tecla", ou so o texto quando nao ha tecla."""
    shown = label.fixed_key or (display_key(key) if key else "")
    return f"{label.text}{KEY_SEPARATOR}{shown}" if shown else label.text


def default_key(action_id: Optional[str]) -> str:
    return _DEFAULT_KEYS.get(action_id or "", "")
