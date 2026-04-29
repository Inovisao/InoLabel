from app.annotation.shared import *


class ModeTogglesMixin:
    def toggle_annotation_mode(self):
        if self.current_frame is None:
            return

        self.annotation_mode = not self.annotation_mode
        if self.annotation_mode and self.pan_mode:
            self.pan_mode = False
        if self.annotation_mode and self.edit_id_mode:
            self.edit_id_mode = False
            self.selected_detection = None
        if self.annotation_mode and self.selection_mode:
            self.selection_mode = False
            self.selected_detection = None
        if self.annotation_mode and self.remove_mode:
            self.remove_mode = False

        if not self.annotation_mode:
            if self.drawing_rect_id is not None:
                self.canvas.delete(self.drawing_rect_id)
                self.drawing_rect_id = None
            self.drawing_start = None
        estado_msg = "ativado" if self.annotation_mode else "desativado"
        print(f"[INFO] Modo anotacao manual {estado_msg}. Clique e arraste para desenhar caixas.")
        self.update_canvas_cursor()
        self.update_status()

    def toggle_selection_mode(self):
        if self.current_frame is None:
            return

        self.selection_mode = not self.selection_mode
        if self.selection_mode:
            self.annotation_mode = False
            self.remove_mode = False
            self.edit_id_mode = False
            self.pan_mode = False
            if self.drawing_rect_id is not None:
                self.canvas.delete(self.drawing_rect_id)
                self.drawing_rect_id = None
            self.drawing_start = None
        else:
            self.selected_detection = None
            if not self.annotation_mode:
                self.annotation_mode = True
        estado_msg = "ativado" if self.selection_mode else "desativado"
        print(f"[INFO] Modo selecionar anotacao {estado_msg}. Clique em uma caixa para trocar classe.")
        self.update_canvas_cursor()
        self.update_status()

    def toggle_remove_mode(self):
        if self.current_frame is None:
            return

        self.remove_mode = not self.remove_mode
        if self.remove_mode and self.edit_id_mode:
            self.edit_id_mode = False
            self.selected_detection = None
        if self.remove_mode and self.selection_mode:
            self.selection_mode = False
            self.selected_detection = None
        if self.remove_mode:
            self.pan_mode = False
            if self.annotation_mode:
                self.annotation_mode = False
            if self.drawing_rect_id is not None:
                self.canvas.delete(self.drawing_rect_id)
                self.drawing_rect_id = None
            self.drawing_start = None
        else:
            if not self.annotation_mode:
                self.annotation_mode = True
        estado_msg = "ativado" if self.remove_mode else "desativado"
        print(f"[INFO] Modo remover anotacao {estado_msg}. Clique sobre uma caixa para remove-la.")
        self.update_canvas_cursor()
        self.update_status()

    def toggle_edit_id_mode(self):
        if self.current_frame is None:
            return

        self.edit_id_mode = not self.edit_id_mode
        if self.edit_id_mode:
            self.pan_mode = False
            if self.selection_mode:
                self.selection_mode = False
                self.selected_detection = None
            if self.annotation_mode:
                self.annotation_mode = False
            if self.remove_mode:
                self.remove_mode = False
        else:
            if not self.annotation_mode:
                self.annotation_mode = True
            self.selected_detection = None
        estado_msg = "ativado" if self.edit_id_mode else "desativado"
        print(f"[INFO] Modo editar ID {estado_msg}. Clique em uma caixa para selecionar.")
        self.update_canvas_cursor()
        self.update_status()
