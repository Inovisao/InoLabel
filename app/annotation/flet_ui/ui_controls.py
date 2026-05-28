"""Flet: controles de teclado e enable/disable de botões."""

from __future__ import annotations

import flet as ft

from app.annotation.keybinds.keybind_mixin import KeybindMixin


class FletUIControlsMixin(KeybindMixin):
    """Substitui UIControlsMixin para ambiente Flet."""

    def _bind_shortcuts(self):
        self.init_keybind_service()

    def _dispatch_keyboard(self, e: ft.KeyboardEvent):
        """Distribuidor central de teclado — chamado por FletMainWindowMixin."""
        key = e.key
        ctrl = e.ctrl
        shift = e.shift

        # Ignora se campo de texto está em foco — não há forma direta de verificar em Flet,
        # então usamos flag _ignore_keyboard que é setada pelos campos de texto.
        if getattr(self, "_ignore_keyboard", False):
            return

        if key == "Escape":
            self.on_quit()
        elif key == " " or key == "Space":
            if hasattr(self, "on_reject"):
                self.on_reject()
        elif key == "Enter":
            if hasattr(self, "on_accept"):
                self.on_accept()
        elif key in "123456789":
            if hasattr(self, "on_class_shortcut"):
                self._on_class_shortcut_flet(int(key))
        elif ctrl and key == "z":
            if hasattr(self, "undo"):
                self.undo()
        elif ctrl and key == "Z":
            if hasattr(self, "redo"):
                self.redo()
        elif ctrl and key == "0":
            if hasattr(self, "reset_zoom"):
                self.reset_zoom()
        else:
            self._try_keybind_action(key, ctrl=ctrl, shift=shift)

    def _on_class_shortcut_flet(self, index: int):
        classes = list(getattr(self, "target_classes", []))
        if 1 <= index <= len(classes):
            self._active_class_name_val = classes[index - 1]
            if hasattr(self, "update_class_panel"):
                self.update_class_panel()

    def _try_keybind_action(self, key: str, ctrl: bool = False, shift: bool = False):
        """Tenta disparar ação via serviço de keybinds."""
        ks = getattr(self, "_keybind_service", None)
        if ks is None:
            return
        try:
            ks.dispatch(key, ctrl=ctrl, shift=shift)
        except Exception:  # pylint: disable=broad-except
            pass

    # ── Enable / disable de controles ─────────────────────────────────────────

    def enable_controls_after_roi(self):
        btns = [
            "accept_button", "reject_button", "annotation_button",
            "remove_button", "selection_button", "pan_button", "export_dataset_button",
        ]
        for name in btns:
            btn = getattr(self, name, None)
            if btn is not None:
                btn.disabled = False
        if not self.tracking_enabled:
            for name in ("apply_id_button", "edit_id_button"):
                btn = getattr(self, name, None)
                if btn is not None:
                    btn.disabled = True
        else:
            for name in ("apply_id_button", "edit_id_button"):
                btn = getattr(self, name, None)
                if btn is not None:
                    btn.disabled = False
        self.page.update()

    def disable_controls_for_roi(self):
        btns = [
            "accept_button", "reject_button", "annotation_button", "remove_button",
            "selection_button", "apply_id_button", "edit_id_button", "export_dataset_button",
        ]
        for name in btns:
            btn = getattr(self, name, None)
            if btn is not None:
                btn.disabled = True
        self.page.update()

    # ── Canvas cursor — compatibilidade ───────────────────────────────────────

    def update_canvas_cursor(self):
        if hasattr(self, "_flet_gesture"):
            cursor = ft.MouseCursor.MOVE if getattr(self, "pan_mode", False) else ft.MouseCursor.PRECISE
            self._flet_gesture.mouse_cursor = cursor
            self.page.update()

    # ── Misc compat ────────────────────────────────────────────────────────────

    def _build_canvas(self):
        pass  # canvas já construído em FletCanvasPanelMixin

    def _bind_canvas_events(self):
        pass  # eventos já registrados no GestureDetector

    def _open_keybind_editor(self):
        if hasattr(self, "open_keybind_editor"):
            self.open_keybind_editor()
