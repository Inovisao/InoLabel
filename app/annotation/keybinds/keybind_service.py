"""Aplica um perfil KeybindMap à janela Tkinter da ferramenta."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from app.annotation.keybinds.actions import ACTION_REGISTRY, ActionDescriptor
from app.annotation.keybinds.keybind_map import KeybindMap
from app.annotation.keybinds.keybind_repository import KeybindRepository

if TYPE_CHECKING:
    import tkinter as tk

# Teclas especiais que precisam de <angle-bracket> no Tkinter
_SPECIAL_KEYS = {
    "Right", "Left", "Up", "Down",
    "Return", "space", "BackSpace", "Delete", "Tab",
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "Home", "End", "Prior", "Next", "Insert",
}

# Teclas modificadoras puras — ignoradas na captura
MODIFIER_KEYSYMS = {
    "Control_L", "Control_R",
    "Shift_L", "Shift_R",
    "Alt_L", "Alt_R", "Meta_L", "Meta_R",
    "Super_L", "Super_R",
    "Caps_Lock", "Num_Lock",
}


def _tk_sequence(key: str) -> str:
    """Converte string interna ('Right', 'd', 'Control-z') para sequência Tkinter."""
    if not key:
        return ""
    # Já tem modifier prefix (ex: "Control-z", "Control-0")
    if "-" in key and not key.startswith("<"):
        return f"<{key}>"
    # Tecla especial sem modifier
    if key in _SPECIAL_KEYS:
        return f"<{key}>"
    # Letra/símbolo simples — bind direto
    return key


def _uppercase_sequence(seq: str) -> Optional[str]:
    """Retorna a variante maiúscula de uma sequência de tecla simples, ou None."""
    if not seq or seq.startswith("<"):
        return None
    if len(seq) == 1 and seq.isalpha():
        return seq.upper()
    return None


class KeybindService:
    # Ações hardcoded que nunca aparecem no editor (quit fica em _bind_shortcuts)
    ALWAYS_UNMANAGED: frozenset = frozenset({"quit"})

    def __init__(self, tool, repository: KeybindRepository):
        self._tool = tool
        self._repo = repository
        self._active_name: str = "arrows"
        self._profiles: Dict[str, KeybindMap] = {}
        self._load_from_repo()

    # ── public API ────────────────────────────────────────────────────────────

    def bind_all(self) -> None:
        """Aplica o perfil ativo (chamado no startup após criar a janela)."""
        self._apply(self._active_name)

    def apply_profile(self, name: str) -> None:
        """Troca para o perfil `name` e rebinda todas as teclas."""
        if name not in self._profiles:
            name = "arrows"
        self._active_name = name
        self._apply(name)
        self._repo.save(self._active_name, self._profiles)

    def get_active_profile(self) -> KeybindMap:
        return self._profiles[self._active_name]

    def get_active_profile_name(self) -> str:
        return self._active_name

    def get_profiles(self) -> Dict[str, KeybindMap]:
        return self._profiles

    def add_profile(self, name: str, base_name: Optional[str] = None) -> KeybindMap:
        """Cria novo perfil copiando `base_name` (ou ativo se None)."""
        source = self._profiles.get(base_name or self._active_name, self._profiles["arrows"])
        new_profile = source.copy()
        new_profile.name = name
        self._profiles[name] = new_profile
        self._repo.save(self._active_name, self._profiles)
        return new_profile

    def delete_profile(self, name: str) -> None:
        """Remove perfil personalizado. Perfis builtin não podem ser deletados."""
        if KeybindRepository.is_builtin(name):
            return
        self._profiles.pop(name, None)
        if self._active_name == name:
            self._active_name = "arrows"
            self._apply("arrows")
        self._repo.save(self._active_name, self._profiles)

    def reset_profile_to_defaults(self, name: str) -> KeybindMap:
        """Restaura perfil para os defaults do ACTION_REGISTRY."""
        defaults = self._repo.get_defaults()
        base = defaults.get(name, defaults["arrows"])
        restored = base.copy()
        restored.name = name
        self._profiles[name] = restored
        if name == self._active_name:
            self._apply(name)
        self._repo.save(self._active_name, self._profiles)
        return restored

    def save_profile(self, profile: KeybindMap) -> None:
        """Persiste alterações feitas diretamente em um perfil."""
        self._profiles[profile.name] = profile
        self._repo.save(self._active_name, self._profiles)

    # ── private helpers ───────────────────────────────────────────────────────

    def _load_from_repo(self) -> None:
        active, profiles = self._repo.load()
        self._active_name = active
        self._profiles = profiles

    def _apply(self, name: str) -> None:
        profile = self._profiles.get(name, self._profiles.get("arrows"))
        if profile is None:
            return
        self._unbind_all()
        for action in ACTION_REGISTRY:
            self._bind_action(action, profile)

    def _unbind_all(self) -> None:
        window: tk.Misc = self._tool.window
        for action in ACTION_REGISTRY:
            for profile in self._profiles.values():
                key = profile.get_key(action.id) or ""
                for seq in self._all_sequences(key):
                    try:
                        window.unbind(seq)
                    except Exception:  # pylint: disable=broad-except
                        pass

    def _bind_action(self, action: ActionDescriptor, profile: KeybindMap) -> None:
        key = profile.get_key(action.id) or ""
        if not key:
            return

        # toggle_edit_id só existe em tracking
        if action.tracking_only and not getattr(self._tool, "tracking_enabled", False):
            return

        handler = getattr(self._tool, action.handler, None)
        if handler is None:
            return

        window: tk.Misc = self._tool.window
        for seq in self._all_sequences(key):
            window.bind(
                seq,
                lambda event, h=handler: self._tool._run_shortcut(event, h),
            )

    def _all_sequences(self, key: str):
        """Retorna todas as sequências Tkinter para uma key (lower + upper)."""
        if not key:
            return []
        seq = _tk_sequence(key)
        if not seq:
            return []
        sequences = [seq]
        upper = _uppercase_sequence(seq)
        if upper:
            sequences.append(upper)
        return sequences
