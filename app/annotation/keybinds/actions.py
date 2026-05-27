"""Registro de todas as ações remapeáveis do InoLabel.

Para adicionar uma nova ação a partir de qualquer mixin:

    from app.annotation.keybinds.actions import ACTION_REGISTRY, ActionDescriptor
    ACTION_REGISTRY.append(ActionDescriptor(
        id="my_action", label="Minha ação", group="Meu Grupo",
        handler="my_method", obb=True,
        default_arrows="m", default_wasd="m",
    ))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ActionDescriptor:
    id: str
    label: str
    group: str
    handler: str
    obb: bool
    default_arrows: str
    default_wasd: str
    tracking_only: bool = False


ACTION_REGISTRY: List[ActionDescriptor] = [
    # ── Navegação ────────────────────────────────────────────────────────────
    ActionDescriptor(
        id="next_frame",
        label="Próximo frame",
        group="Navegação",
        handler="on_next_saved",
        obb=True,
        default_arrows="Right",
        default_wasd="d",
    ),
    ActionDescriptor(
        id="prev_frame",
        label="Frame anterior",
        group="Navegação",
        handler="on_prev_saved",
        obb=True,
        default_arrows="Left",
        default_wasd="a",
    ),
    # ── Seleção ──────────────────────────────────────────────────────────────
    ActionDescriptor(
        id="toggle_selection",
        label="Modo de seleção",
        group="Seleção",
        handler="toggle_selection_mode",
        obb=True,
        default_arrows="s",
        default_wasd="",  # conflito com next_frame no wasd → sem bind por padrão
    ),
    # ── Fluxo ────────────────────────────────────────────────────────────────
    ActionDescriptor(
        id="accept",
        label="Validar imagem",
        group="Fluxo",
        handler="on_accept",
        obb=True,
        default_arrows="Return",
        default_wasd="Return",
    ),
    ActionDescriptor(
        id="reject",
        label="Rejeitar / avançar",
        group="Fluxo",
        handler="on_reject",
        obb=True,
        default_arrows="space",
        default_wasd="space",
    ),
    # ── Anotação ─────────────────────────────────────────────────────────────
    ActionDescriptor(
        id="toggle_draw",
        label="Modo de anotação (on/off)",
        group="Anotação",
        handler="toggle_annotation_mode",
        obb=True,
        default_arrows="k",
        default_wasd="k",
    ),
    ActionDescriptor(
        id="toggle_pan",
        label="Mover imagem (on/off)",
        group="Anotação",
        handler="toggle_pan_mode",
        obb=True,
        default_arrows="h",
        default_wasd="h",
    ),
    ActionDescriptor(
        id="toggle_remove",
        label="Remover anotação (on/off)",
        group="Anotação",
        handler="toggle_remove_mode",
        obb=True,
        default_arrows="",  # sem bind padrão — atribuir via editor
        default_wasd="",
    ),
    ActionDescriptor(
        id="reset_roi",
        label="Redefinir ROI",
        group="Anotação",
        handler="reset_roi",
        obb=True,
        default_arrows="r",
        default_wasd="r",
    ),
    # ── Geral ────────────────────────────────────────────────────────────────
    ActionDescriptor(
        id="undo",
        label="Desfazer",
        group="Geral",
        handler="undo_last_action",
        obb=True,
        default_arrows="Control-z",
        default_wasd="Control-z",
    ),
    ActionDescriptor(
        id="reset_zoom",
        label="Ajustar zoom",
        group="Geral",
        handler="reset_zoom",
        obb=True,
        default_arrows="Control-0",
        default_wasd="Control-0",
    ),
    # ── Imagem ───────────────────────────────────────────────────────────────
    ActionDescriptor(
        id="rotate_cw",
        label="Rotacionar 90° horário",
        group="Imagem",
        handler="rotate_frame_cw",
        obb=True,
        default_arrows="",
        default_wasd="",
    ),
    ActionDescriptor(
        id="rotate_ccw",
        label="Rotacionar 90° anti-horário",
        group="Imagem",
        handler="rotate_frame_ccw",
        obb=True,
        default_arrows="",
        default_wasd="",
    ),
    # ── Tracking (apenas no modo tracking) ──────────────────────────────────
    ActionDescriptor(
        id="toggle_edit_id",
        label="Editar ID de tracking",
        group="Tracking",
        handler="toggle_edit_id_mode",
        obb=False,
        tracking_only=True,
        default_arrows="e",
        default_wasd="e",
    ),
]
