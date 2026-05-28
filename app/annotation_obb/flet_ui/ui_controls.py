"""Flet: controles OBB — teclado e enable/disable de botões."""

from __future__ import annotations

import flet as ft

from app.annotation.keybinds.keybind_mixin import KeybindMixin


class FletOBBUIControlsMixin(KeybindMixin):
    """Substitui OBBUIControlsMixin para Flet."""

    def _bind_shortcuts(self):
        self.init_keybind_service()

    def _dispatch_keyboard(self, e: ft.KeyboardEvent):
        if getattr(self, "_ignore_keyboard", False):
            return
        key = e.key
        ctrl = e.ctrl
        shift = e.shift
        if key == "Escape":
            self.on_quit()
        elif key == " " or key == "Space":
            if hasattr(self, "on_reject"):
                self.on_reject()
        elif key == "Enter":
            if hasattr(self, "on_accept"):
                self.on_accept()
        elif key in "123456789":
            self._on_class_shortcut_flet(int(key))
        elif ctrl and key == "z":
            if hasattr(self, "undo"):
                self.undo()
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
        ks = getattr(self, "_keybind_service", None)
        if ks is None:
            return
        try:
            ks.dispatch(key, ctrl=ctrl, shift=shift)
        except Exception:  # pylint: disable=broad-except
            pass

    def enable_controls_after_roi(self):
        for name in (
            "accept_button", "reject_button", "annotation_button",
            "remove_button", "selection_button", "pan_button",
            "export_dataset_button",
        ):
            btn = getattr(self, name, None)
            if btn is not None:
                btn.disabled = False
        # OBB não usa edit_id nem apply_id
        for name in ("apply_id_button", "edit_id_button"):
            btn = getattr(self, name, None)
            if btn is not None:
                btn.disabled = True
        self.page.update()

    def disable_controls_for_roi(self):
        for name in (
            "accept_button", "reject_button", "annotation_button",
            "remove_button", "selection_button", "apply_id_button",
            "edit_id_button", "export_dataset_button",
        ):
            btn = getattr(self, name, None)
            if btn is not None:
                btn.disabled = True
        self.page.update()

    def update_canvas_cursor(self):
        if hasattr(self, "_flet_gesture"):
            cursor = ft.MouseCursor.MOVE if getattr(self, "pan_mode", False) else ft.MouseCursor.PRECISE
            self._flet_gesture.mouse_cursor = cursor
            self.page.update()

    def _build_canvas(self):
        pass  # canvas já construído em FletCanvasPanelMixin

    def _bind_canvas_events(self):
        pass  # eventos já registrados no GestureDetector

    def update_pan_button(self):
        if not hasattr(self, "pan_button"):
            return
        on = getattr(self, "pan_mode", False)
        self.pan_button.text = f"Mover imagem  {'ON ' if on else 'OFF'}  (H)"
        if hasattr(self, "page"):
            self.page.update()

    def update_annotation_button(self):
        if not hasattr(self, "annotation_button"):
            return
        on = getattr(self, "annotation_mode", False)
        self.annotation_button.text = f"Anotação manual  {'ON ' if on else 'OFF'}  (K)"
        if hasattr(self, "page"):
            self.page.update()

    def update_remove_button(self):
        if not hasattr(self, "remove_button"):
            return
        on = getattr(self, "remove_mode", False)
        self.remove_button.text = f"Remover anotação  {'ON ' if on else 'OFF'}"
        if hasattr(self, "page"):
            self.page.update()

    def update_selection_button(self):
        if not hasattr(self, "selection_button"):
            return
        on = getattr(self, "selection_mode", False)
        self.selection_button.text = f"Selecionar anotação  {'ON ' if on else 'OFF'}  (S)"
        if hasattr(self, "page"):
            self.page.update()

    def update_edit_id_button(self):
        if not hasattr(self, "edit_id_button"):
            return
        self.edit_id_button.text = "Editar ID (indisponível)"
        if hasattr(self, "page"):
            self.page.update()
