"""Dataset-level actions such as deleting images and exporting folders."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

from app.classification.dataset import export_classification_dataset
from app.ui.file_manager import reveal_path


class ClassificationDatasetActionsMixin:
    def on_remove_current_image(self):
        if self.current_index >= len(self.images):
            return
        source_path = self.images[self.current_index]
        image_path = self._display_path_for_source(source_path)
        confirmed = messagebox.askyesno(
            "Remover imagem",
            f"Remover esta imagem do dataset e apagar o arquivo?\n\n{image_path}",
            parent=self.root,
        )
        if not confirmed:
            return
        try:
            if image_path.exists():
                image_path.unlink()
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Falha ao remover imagem", str(exc), parent=self.root)
            return

        self.records = [record for record in self.records if record.source_path != source_path]
        self.undo_stack = [record for record in self.undo_stack if record.source_path != source_path]
        removed_name = image_path.name
        self.images.pop(self.current_index)
        self.source_image_count = len(self.images)
        if self.current_index >= len(self.images):
            self.current_index = max(0, len(self.images) - 1)
        self._save_state()
        self.info_var.set(f"Imagem removida do dataset: {removed_name}")
        self._load_current_image(skip_classified=False)
        self._focus_navigation_surface()

    def on_export_dataset(self):
        self._save_state()
        selected_dir = filedialog.askdirectory(
            title="Selecione a pasta de destino do dataset",
            parent=self.root,
            mustexist=True,
        )
        if not selected_dir:
            return
        export_root = self._resolve_export_dataset_path(Path(selected_dir))
        try:
            report = export_classification_dataset(
                records=self.records,
                classes=self.classes,
                class_directories=self.class_directories,
                dataset_root=export_root,
            )
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Falha ao exportar dataset", str(exc), parent=self.root)
            self.info_var.set(f"Falha ao exportar dataset: {exc}")
            return
        skipped = len(report["skipped"])
        message = f"Dataset exportado em: {report['dataset_root']} | {report['copied']} imagens"
        if skipped:
            message += f" | {skipped} ignorada(s)"
        self.info_var.set(message)
        print(f"[INFO] {message}")

    def _resolve_export_dataset_path(self, selected_dir: Path) -> Path:
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

    def on_quit(self):
        self._save_state()
        self.root.destroy()

    def on_open_output_folder(self):
        if not reveal_path(self.output_dir):
            self.info_var.set(f"Nao foi possivel abrir: {self.output_dir}")
