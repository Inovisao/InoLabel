"""Status e queries de estado puras para o modo OBB — sem UI."""

from backend.annotation_obb.shared import *


class OBBDisplayStatusMixin:
    def current_deletable_image_path(self) -> Optional[Path]:
        record = self.current_review_record()
        if record is not None:
            file_name = str(record.get("file_name", "")).strip()
            return self.output_images_dir / file_name if file_name else None
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            return self.current_source_image_path
        return None

    def current_display_file_name(self) -> str:
        record = self.current_review_record()
        if record is not None:
            return str(record.get("file_name", "-"))
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            return self.current_source_image_path.name
        return f"{self.video_name}_frame_{self.frame_index:05d}.jpg"

    def current_open_target_path(self) -> Optional[Path]:
        record = self.current_review_record()
        if record is not None:
            file_name = record.get("file_name")
            if file_name:
                saved_path = self.output_images_dir / str(file_name)
                if saved_path.exists():
                    return saved_path
            return None
        file_name = self.current_frame_file_name()
        if file_name:
            saved_path = self.output_images_dir / file_name
            if saved_path.exists():
                return saved_path
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            if self.current_source_image_path.exists():
                return self.current_source_image_path
        return None

    def build_status_message(self) -> str:
        if self.review_idx is not None and self.saved_records:
            return f"Revisao OBB {self.review_idx + 1}/{len(self.saved_records)} · {self.video_name}"
        if self.pan_mode:
            mode = "Pan ON"
        elif self.annotation_mode:
            mode = "OBB manual ON"
        elif self.remove_mode:
            mode = "Remocao OBB ON"
        elif self.selection_mode:
            mode = "Selecao OBB ON"
        else:
            mode = self.task_mode.label
        return f"{mode} · {self.video_name} · Frame {self.frame_index}"
