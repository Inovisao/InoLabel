"""Applies a KeybindMap profile to the tool's Tkinter window."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from app.annotation.keybinds.actions import ACTION_REGISTRY, ActionDescriptor
from app.annotation.keybinds.keybind_map import KeybindMap
from app.annotation.keybinds.keybind_repository import KeybindRepository

if TYPE_CHECKING:
    import tkinter as tk

# Special keys that require <angle-bracket> notation in Tkinter
_SPECIAL_KEYS = {
    "Right", "Left", "Up", "Down",
    "Return", "space", "BackSpace", "Delete", "Tab",
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "Home", "End", "Prior", "Next", "Insert",
}

# Pure modifier keys — ignored during capture
MODIFIER_KEYSYMS = {
    "Control_L", "Control_R",
    "Shift_L", "Shift_R",
    "Alt_L", "Alt_R", "Meta_L", "Meta_R",
    "Super_L", "Super_R",
    "Caps_Lock", "Num_Lock",
}


def _tk_sequence(key: str) -> str:
    """Converts an internal string ('Right', 'd', 'Control-z') to a Tkinter sequence."""
    if not key:
        return ""
    # Already has a modifier prefix (e.g. "Control-z", "Control-0")
    if "-" in key and not key.startswith("<"):
        return f"<{key}>"
    # Special key without a modifier
    if key in _SPECIAL_KEYS:
        return f"<{key}>"
    # Plain letter/symbol — bind directly
    return key


def _uppercase_sequence(seq: str) -> Optional[str]:
    """Returns the uppercase variant of a simple key sequence, or None."""
    if not seq or seq.startswith("<"):
        return None
    if len(seq) == 1 and seq.isalpha():
        return seq.upper()
    return None


class KeybindService:
    # Hardcoded actions that never appear in the editor (quit is handled in _bind_shortcuts)
    ALWAYS_UNMANAGED: frozenset = frozenset({"quit"})

    def __init__(self, tool, repository: KeybindRepository):
        self._tool = tool
        self._repo = repository
        self._active_name: str = "arrows"
        self._profiles: Dict[str, KeybindMap] = {}
        self._load_from_repo()

    # ── public API ────────────────────────────────────────────────────────────

    def bind_all(self) -> None:
        """Applies the active profile (called at startup after the window is created)."""
        self._apply(self._active_name)

    def apply_profile(self, name: str) -> None:
        """Switches to profile `name` and rebinds all keys."""
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
        """Creates a new profile by copying `base_name` (or the active profile if None)."""
        source = self._profiles.get(base_name or self._active_name, self._profiles["arrows"])
        new_profile = source.copy()
        new_profile.name = name
        self._profiles[name] = new_profile
        self._repo.save(self._active_name, self._profiles)
        return new_profile

    def delete_profile(self, name: str) -> None:
        """Removes a custom profile. Built-in profiles cannot be deleted."""
        if KeybindRepository.is_builtin(name):
            return
        self._profiles.pop(name, None)
        if self._active_name == name:
            self._active_name = "arrows"
            self._apply("arrows")
        self._repo.save(self._active_name, self._profiles)

    def reset_profile_to_defaults(self, name: str) -> KeybindMap:
        """Resets a profile to the ACTION_REGISTRY defaults."""
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
        """Persists changes made directly to a profile."""
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

        # toggle_edit_id only exists in tracking mode
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
        """Returns all Tkinter sequences for a key (lowercase + uppercase)."""
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
