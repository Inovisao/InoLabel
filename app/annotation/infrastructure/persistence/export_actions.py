"""Ações de exportação disparadas pela UI (COCO, YOLO, dataset completo)."""

from app.annotation.shared import *
from app.dataset_export import export_detection_coco_json, export_yolo_dataset
from datetime import datetime


class ExportActionsMixin:
    def sync_export_metadata(self):
        if self.coco_detection_export_path.exists():
            export_detection_coco_json(self.build_coco_payload(), self.coco_detection_export_path)
        if (self.yolo_dataset_dir / "data.yaml").exists():
            export_yolo_dataset(
                self.build_coco_payload(),
                source_images_dir=self.output_images_dir,
                dataset_root=self.yolo_dataset_dir,
            )

    def on_save_coco_json(self):
        self.autosave_current_frame(reason="exportar .coco.json")
        if not self.images:
            self.info_var.set("Nenhuma imagem salva para exportar em .coco.json.")
            return
        try:
            self.write_annotations()
            converted = export_detection_coco_json(self.build_coco_payload(), self.coco_detection_export_path)
            message = (
                f"COCO salvo em {self.coco_detection_export_path} | "
                f"imagens={len(converted['images'])} anotacoes={len(converted['annotations'])}"
            )
            self.info_var.set(message)
            print(f"[INFO] {message}")
        except Exception as exc:  # pylint: disable=broad-except
            message = f"Falha ao exportar .coco.json: {exc}"
            self.info_var.set(message)
            print(f"[ERRO] {message}")

    def on_save_yaml(self):
        self.autosave_current_frame(reason="exportar .yaml")
        if not self.images:
            self.info_var.set("Nenhuma imagem salva para exportar em .yaml.")
            return
        try:
            self.write_annotations()
            report = export_yolo_dataset(
                self.build_coco_payload(),
                source_images_dir=self.output_images_dir,
                dataset_root=self.yolo_dataset_dir,
            )
            message = (
                f"YOLO salvo em {report['dataset_root']} | "
                f"data.yaml={report['data_yaml']} | splits={report['images_per_split']} | "
                f"vazias={report['empty_images_per_split']}"
            )
            self.info_var.set(message)
            print(f"[INFO] {message}")
            if report["images_without_annotation"]:
                print(
                    f"[AVISO] Imagens sem anotacao: "
                    f"{len(report['images_without_annotation'])} -> {report['images_without_annotation'][:10]}"
                )
            if report["malformed_labels"]:
                print(
                    f"[AVISO] Labels mal formatados ignorados: "
                    f"{len(report['malformed_labels'])} -> {report['malformed_labels'][:10]}"
                )
        except Exception as exc:  # pylint: disable=broad-except
            message = f"Falha ao exportar .yaml: {exc}"
            self.info_var.set(message)
            print(f"[ERRO] {message}")

    def prepare_output_dataset(self):
        self.autosave_current_frame(reason="exportar dataset")
        self.write_annotations()
        return export_yolo_dataset(
            self.build_coco_payload(),
            source_images_dir=self.output_images_dir,
            dataset_root=self.yolo_dataset_dir,
        )

    def resolve_export_dataset_path(self, selected_dir: Path) -> Path:
        selected_dir = Path(selected_dir).expanduser()
        output_dir = self.output_dir.resolve()
        selected_resolved = selected_dir.resolve()
        if selected_resolved == output_dir or output_dir in selected_resolved.parents:
            candidate = output_dir.with_name(f"{output_dir.name}_export")
        elif selected_dir.name == self.output_dir.name:
            candidate = selected_dir
        else:
            candidate = selected_dir / self.output_dir.name
        candidate = candidate.resolve()
        if candidate == output_dir or output_dir in candidate.parents:
            candidate = output_dir.with_name(f"{output_dir.name}_export")
        if not candidate.exists():
            return candidate
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return candidate.with_name(f"{candidate.name}_{stamp}")

    def export_output_dataset_to(self, selected_dir: Path) -> Path:
        if self.current_frame is None and not self.images and not self.annotations:
            raise RuntimeError("Nenhuma imagem/anotacao salva para exportar.")
        self.prepare_output_dataset()
        destination = self.resolve_export_dataset_path(selected_dir)
        output_dir = self.output_dir.resolve()
        destination = destination.resolve()
        if destination == output_dir or output_dir in destination.parents:
            raise RuntimeError("Destino de exportacao nao pode ser a propria pasta de output ou uma subpasta dela.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.output_dir, destination)
        return destination

    def on_export_dataset(self):
        selected = filedialog.askdirectory(
            title="Escolha onde salvar o output_dataset",
            mustexist=True,
            parent=self.window,
        )
        if not selected:
            return
        try:
            destination = self.export_output_dataset_to(Path(selected))
            message = f"Dataset exportado para {destination}"
            self.info_var.set(message)
            print(f"[INFO] {message}")
        except Exception as exc:  # pylint: disable=broad-except
            message = f"Falha ao exportar dataset: {exc}"
            self.info_var.set(message)
            print(f"[ERRO] {message}")
