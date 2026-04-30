from app.annotation_obb.shared import *
from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset


class OBBExportActionsMixin:
    def sync_export_metadata(self):
        return None

    def on_export_dataset(self):
        try:
            self.autosave_current_frame(reason="exportar OBB")
            self.write_annotations()
            payload = self.build_coco_payload()
            export_root = self.output_dir / "yolo_obb_dataset"
            summary = export_yolo_obb_dataset(payload, export_root, self.output_images_dir)
            msg = f"YOLO OBB exportado: {summary['images']} imagens | {summary['labels']} anotacoes"
            self.info_var.set(msg)
            print(f"[INFO] {msg} em {export_root}")
        except Exception as exc:  # pylint: disable=broad-except
            self.info_var.set(f"Falha ao exportar YOLO OBB: {exc}")
            print(f"[ERRO] Falha ao exportar YOLO OBB: {exc}")
