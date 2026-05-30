"""Integration mixin for the keybind system into the UI mixins.

Drop-in for UIControlsMixin and OBBUIControlsMixin: replaces apply_key_mapping
and exposes open_keybind_editor / update_key_mapping_button.
"""

from __future__ import annotations

from app.annotation.keybinds.keybind_repository import KeybindRepository
from app.annotation.keybinds.keybind_service import KeybindService


class KeybindMixin:
    def init_keybind_service(self) -> None:
        """Creates the service and applies the saved profile. Call at the end of _bind_shortcuts."""
        repo = KeybindRepository()
        self._keybind_service = KeybindService(self, repo)
        self._keybind_service.bind_all()
        self.update_key_mapping_button()

    # ── backward compatibility ────────────────────────────────────────────────

    def apply_key_mapping(self, mode: str) -> None:
        """Maintains compatibility with legacy calls — delegates to the service."""
        if hasattr(self, "_keybind_service"):
            self._keybind_service.apply_profile(mode)
            self.update_key_mapping_button()

    # ── editor ────────────────────────────────────────────────────────────────

    def open_keybind_editor(self) -> None:
        """Opens (or raises) the visual remapping window."""
        existing = getattr(self, "_keybind_editor_window", None)
        if existing is not None:
            try:
                existing.lift()
                existing.focus_force()
                return
            except Exception:  # pylint: disable=broad-except
                self._keybind_editor_window = None

        from app.annotation.keybinds.keybind_editor import KeybindEditorWindow

        win = KeybindEditorWindow(
            parent=self.window,
            service=self._keybind_service,
            tool=self,
        )
        self._keybind_editor_window = win

    # ── button label ─────────────────────────────────────────────────────────

    def update_key_mapping_button(self) -> None:
        if not hasattr(self, "key_mapping_button"):
            return
        name = getattr(self, "_keybind_service", None)
        if name is not None:
            label = self._keybind_service.get_active_profile_name()
        else:
            label = getattr(self, "key_mapping_mode", "arrows")
        self.key_mapping_button.config(text=f"Atalhos: {label}")
