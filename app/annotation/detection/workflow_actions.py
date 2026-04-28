from app.annotation.shared import *


class WorkflowActionsMixin:
    def _delete_review_image(self, record: dict):
        file_name = str(record.get("file_name", "")).strip()
        image_id = int(record.get("image_id") or 0)
        current_idx = self.review_idx if self.review_idx is not None else 0

        removed_annotations = self.delete_image_annotations(image_id)
        file_removed = self.remove_image_file(file_name)
        self.remove_exported_dataset_files(file_name)
        self.write_annotations()
        self.sync_export_metadata()

        self.saved_records.pop(current_idx)
        self.selected_detection = None

        message = f"Imagem deletada: {file_name} | anotacoes removidas: {removed_annotations}"
        if not file_removed:
            message += " | arquivo ja nao existia em output/images"
        print(f"[INFO] {message}")

        if self.saved_records:
            next_idx = min(current_idx, len(self.saved_records) - 1)
            self.go_to_saved_frame(next_idx)
            self.info_var.set(message)
            return

        self.exit_review_mode()
        self.info_var.set(message)

    def _delete_current_source_image(self, image_path: Path):
        if self.current_source_type != "images":
            raise RuntimeError("A exclusao direta da fonte atual so e suportada para sequencias de imagens.")
        try:
            image_path.unlink()
        except FileNotFoundError:
            pass
        self.remove_current_image_from_sequence(image_path)
        self.current_source_image_path = None
        self.current_frame = None
        self.selected_detection = None
        self.current_detections = []
        self.manual_detections = []
        self.info_var.set(f"Imagem removida da sequencia: {image_path.name}")
        print(f"[INFO] Imagem removida da sequencia: {image_path}")
        self.load_next_frame()

    def on_delete_image(self):
        """Exclui a imagem salva em revisao ou a imagem atual da sequencia."""
        record = self.current_review_record()
        delete_target = self.current_deletable_image_path()
        if record is None and delete_target is None:
            self.info_var.set("Nenhuma imagem disponivel para exclusao neste momento.")
            return

        if record is not None:
            file_name = str(record.get("file_name", "")).strip()
            prompt = f'Deletar "{file_name}" do dataset e remover suas anotacoes?'
        else:
            prompt = f'Deletar a imagem de origem "{delete_target.name}" da sequencia atual?'

        confirmed = messagebox.askyesno(
            "Confirmar exclusao",
            prompt,
        )
        if not confirmed:
            return

        try:
            if record is not None:
                self._delete_review_image(record)
            else:
                self._delete_current_source_image(delete_target)
        except Exception as exc:  # pylint: disable=broad-except
            target_name = str(record.get("file_name", "")).strip() if record is not None else delete_target.name
            self.info_var.set(f"Falha ao deletar {target_name}: {exc}")
            print(f"[ERRO] Falha ao deletar {target_name}: {exc}")

    def on_accept(self):
        """Persistir anotacoes quando o usuario aprova o frame."""
        if self.current_frame is None:
            return
        detections_to_save = list(self.current_detections) + list(self.manual_detections)
        if self.review_idx is not None and self.saved_records:
            record = self.saved_records[self.review_idx]
            image_id, file_name = self.store_annotations(
                detections_to_save, existing_image_id=record.get("image_id"), existing_file_name=record.get("file_name")
            )
            self.update_manual_memory_after_accept(detections_to_save)
            self.update_saved_record(self.review_idx, detections_to_save, image_id, file_name)
            self.write_annotations()
            self.advance_after_review_accept()
            return
        image_id, file_name = self.store_annotations(detections_to_save)
        self.write_annotations()
        if detections_to_save:
            self.update_manual_memory_after_accept(detections_to_save)
        self.append_saved_record(detections_to_save, image_id, file_name)
        self.load_next_frame()

    def on_reject(self):
        """Ignora o frame atual e avanca para o proximo."""
        if self.review_idx is not None:
            self.exit_review_mode()
            return
        self.load_next_frame()

    def on_quit(self):
        """Encerra o processo de anotacao."""
        self.finish_processing("Processo encerrado pelo usuario.")

    # ===================== ANOTACOES =====================

    def update_manual_memory_after_accept(self, detections: List[Detection]):
        """Atualiza memoria de tracks manuais para reaproveitar ids."""
        if not self.tracking_enabled:
            return
        for det in detections:
            if det.source != "manual" or det.track_id is None:
                continue
            self.manual_track_memory[det.track_id] = {"bbox": det.original_bbox.copy()}

    @staticmethod
    def clone_detection(det: Detection) -> Detection:
        """Cria uma copia profunda de Detection."""
        return Detection(
            original_bbox=det.original_bbox.copy(),
            warp_bbox=det.warp_bbox.copy() if det.warp_bbox is not None else None,
            confidence=det.confidence,
            category_id=det.category_id,
            track_id=det.track_id,
            source=det.source,
            internal_id=det.internal_id,
        )
