"""Status e queries de estado puras — sem dependencias de UI."""

from backend.annotation.shared import *


class DisplayStatusMixin:
    def current_review_record(self) -> Optional[dict]:
        if self.review_idx is None or not self.saved_records:
            return None
        if self.review_idx < 0 or self.review_idx >= len(self.saved_records):
            return None
        return self.saved_records[self.review_idx]

    def current_deletable_image_path(self) -> Optional[Path]:
        record = self.current_review_record()
        if record is not None:
            file_name = str(record.get("file_name", "")).strip()
            if not file_name:
                return None
            return self.output_images_dir / file_name
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            return self.current_source_image_path
        return None

    def build_status_message(self) -> str:
        if self.review_idx is not None and self.saved_records:
            return f"Revisao {self.review_idx + 1}/{len(self.saved_records)} · {self.video_name}"
        if self.pan_mode:
            mode = "Pan ON"
        elif self.annotation_mode:
            mode = "Anotacao manual ON"
        elif self.remove_mode:
            mode = "Remocao ON"
        elif self.edit_id_mode and self.tracking_enabled:
            mode = "Editar ID ON"
        else:
            mode = self.task_mode.label
        return f"{mode} · {self.video_name} · Frame {self.frame_index}"

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
