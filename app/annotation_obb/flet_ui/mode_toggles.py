"""Flet: toggles de modo OBB — implementação autônoma sem herança Tkinter."""

from __future__ import annotations


class FletOBBModeTogglesMixin:
    """Standalone — sem herança de OBBModeTogglesMixin ou ModeTogglesMixin."""

    def _clear_drawing_canvas_state(self):
        self.drawing_rect_id = None
        self.drawing_start = None
        if hasattr(self, "_hide_drawing_rect"):
            self._hide_drawing_rect()

    def toggle_annotation_mode(self):
        if self.current_frame is None:
            return
        self.annotation_mode = not self.annotation_mode
        if self.annotation_mode and self.pan_mode:
            self.pan_mode = False
        if self.annotation_mode and self.selection_mode:
            self.selection_mode = False
            self.selected_detection = None
        if self.annotation_mode and self.remove_mode:
            self.remove_mode = False
        if not self.annotation_mode:
            self._clear_drawing_canvas_state()
        self.update_canvas_cursor()
        self.update_status()

    def toggle_selection_mode(self):
        if self.current_frame is None:
            return
        self.selection_mode = not self.selection_mode
        if self.selection_mode:
            self.annotation_mode = False
            self.remove_mode = False
            self.pan_mode = False
            self._clear_drawing_canvas_state()
        else:
            self.selected_detection = None
            if not self.annotation_mode:
                self.annotation_mode = True
        self.update_canvas_cursor()
        self.update_status()

    def toggle_remove_mode(self):
        if self.current_frame is None:
            return
        self.remove_mode = not self.remove_mode
        if self.remove_mode and self.selection_mode:
            self.selection_mode = False
            self.selected_detection = None
        if self.remove_mode:
            self.pan_mode = False
            if self.annotation_mode:
                self.annotation_mode = False
            self._clear_drawing_canvas_state()
        else:
            if not self.annotation_mode:
                self.annotation_mode = True
        self.update_canvas_cursor()
        self.update_status()

    def toggle_edit_id_mode(self):
        print("[INFO] O modo OBB MVP não usa edição de ID.")

    def toggle_pan_mode(self):
        self.pan_mode = not self.pan_mode
        if self.pan_mode:
            self.annotation_mode = False
            self.remove_mode = False
            self.selection_mode = False
        self._pan_start_x = None
        self.update_annotation_button()
        self.update_remove_button()
        self.update_selection_button()
        self.update_canvas_cursor()
        self.info_var.set("Pan ON: arraste a imagem para mover." if self.pan_mode else "Pan OFF.")
        self.update_status()
