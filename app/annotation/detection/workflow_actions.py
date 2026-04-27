from app.annotation.shared import *


class WorkflowActionsMixin:
    def on_accept(self):
        """Persistir anotacoes quando o usuario aprova o frame."""
        if self.current_frame is None:
            return
        detections_to_save = list(self.current_detections) + list(self.manual_detections)
        if detections_to_save:
            if self.review_idx is not None and self.saved_records:
                record = self.saved_records[self.review_idx]
                image_id, file_name = self.store_annotations(
                    detections_to_save, existing_image_id=record["image_id"], existing_file_name=record["file_name"]
                )
                self.update_manual_memory_after_accept(detections_to_save)
                self.update_saved_record(self.review_idx, detections_to_save, image_id, file_name)
                self.write_annotations()
                self.advance_after_review_accept()
                return
            image_id, file_name = self.store_annotations(detections_to_save)
            self.write_annotations()
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
        for det in detections:
            if det.source != "manual":
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

