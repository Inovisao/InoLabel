"""Ciclo de vida da sessão de anotação: autosave, encerramento e loop principal."""

from app.annotation.shared import *


class LifecycleMixin:
    def autosave_current_frame(self, *, reason: str = "") -> Optional[Tuple[int, str]]:
        if self.current_frame is None or getattr(self, "closed", False):
            return None
        if getattr(self, "_autosaving", False):
            return None
        file_name = self.current_frame_file_name()
        existing = self.find_image_record_by_file_name(file_name) if file_name else None
        existing_id = int(existing["id"]) if existing is not None else None
        existing_file = str(existing["file_name"]) if existing is not None else None
        try:
            self._autosaving = True
            detections = self.detections_to_save()
            image_id, saved_file = self.store_annotations(
                detections,
                existing_image_id=existing_id,
                existing_file_name=existing_file,
            )
            self.write_annotations()
            self.update_manual_memory_after_accept(detections)
            self.remember_saved_record(detections, image_id, saved_file)
            msg = f"Autosave concluido: {saved_file}"
            if reason:
                msg += f" ({reason})"
            print(f"[INFO] {msg}")
            return image_id, saved_file
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[ERRO] Falha no autosave: {exc}")
            return None
        finally:
            self._autosaving = False

    def finish_processing(self, message: str):
        if self.closed:
            return
        self.autosave_current_frame(reason="encerramento")
        self.closed = True
        key_mapping_dialog = getattr(self, "_key_mapping_dialog", None)
        if key_mapping_dialog is not None:
            try:
                key_mapping_dialog.destroy()
            except Exception:  # pylint: disable=broad-except
                pass
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.window.unbind("<Return>")
        self.window.unbind("<space>")
        self.window.unbind("<Escape>")
        self.accept_button.config(state=tk.DISABLED)
        self.reject_button.config(state=tk.DISABLED)
        self.quit_button.config(state=tk.DISABLED)
        self.delete_image_button.config(state=tk.DISABLED)
        self.pan_button.config(state=tk.DISABLED)
        self.save_yaml_button.config(state=tk.DISABLED)
        self.save_coco_button.config(state=tk.DISABLED)
        self.export_dataset_button.config(state=tk.DISABLED)
        if self.images or self.annotations:
            self.write_annotations()
        if self.homographies:
            with open(self.homography_path, "w", encoding="utf-8") as f:
                json.dump(self.homographies, f, indent=4, ensure_ascii=False)
        self.info_var.set(message)
        try:
            self.window.after(500, self.window.destroy)
        except Exception:  # pylint: disable=broad-except
            try:
                self.window.destroy()
            except Exception:
                pass

    def run(self):
        self.window.mainloop()
