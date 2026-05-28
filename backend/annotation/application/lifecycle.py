"""Ciclo de vida da sessao de anotacao: autosave e encerramento."""

from backend.annotation.shared import *


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

    def finish_processing(self, message: str = ""):
        if getattr(self, "closed", False):
            return
        self.autosave_current_frame(reason="encerramento")
        self.closed = True
        try:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[AVISO] Falha ao liberar fonte: {exc}")
        try:
            if self.images or self.annotations:
                self.write_annotations()
                self.backup_annotations_file()
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[ERRO] Falha ao salvar anotacoes no encerramento: {exc}")
        try:
            if self.homographies:
                with open(self.homography_path, "w", encoding="utf-8") as f:
                    json.dump(self.homographies, f, indent=4, ensure_ascii=False)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[ERRO] Falha ao salvar homografias no encerramento: {exc}")
        if message:
            print(f"[INFO] {message}")
