"""Class management and image-to-class assignment actions."""

from __future__ import annotations

from tkinter import messagebox

from app.classification.dataset import (
    add_class_directory,
    class_directory_has_files,
    classify_image_source,
    remove_class_directory,
)


class ClassificationClassActionsMixin:
    def on_class_selected(self, class_name: str):
        if self.current_index >= len(self.images):
            return
        source_path = self.images[self.current_index]
        previous_record = self._record_for_source(source_path)
        try:
            record = classify_image_source(
                source_path,
                class_name=class_name,
                output_dir=self.output_dir,
                class_directories=self.class_directories,
            )
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Falha ao classificar", str(exc), parent=self.root)
            return
        if previous_record is not None:
            self._remove_previous_classification(previous_record)
        self.records.append(record)
        self.undo_stack.append(record)
        self._save_state()
        self.info_var.set(f"Associada a {class_name}: {source_path.name}")
        self.current_index += 1
        self._load_current_image()
        self._focus_navigation_surface()

    def on_add_class(self):
        class_name = self.new_class_var.get().strip()
        if not class_name:
            return
        if class_name in self.classes:
            self.info_var.set(f"Classe ja existe: {class_name}")
            self.new_class_var.set("")
            return
        add_class_directory(self.output_dir, class_name, self.class_directories)
        self.classes.append(class_name)
        self.new_class_var.set("")
        self._save_state()
        self._bind_shortcuts()
        self._update_status()
        self.info_var.set(f"Classe adicionada: {class_name}")
        self._focus_navigation_surface()

    def on_remove_class(self, class_name: str):
        if len(self.classes) <= 1:
            self.info_var.set("Mantenha ao menos uma classe.")
            return
        class_records = [record for record in self.records if record.class_name == class_name]
        has_files = class_directory_has_files(self.output_dir, class_name, self.class_directories)
        message = f'Remover a classe "{class_name}" da interface e do estado?'
        if class_records:
            message += f"\n\n{len(class_records)} registro(s) desta classe serao removidos do estado."
        if has_files:
            message += "\n\nA subpasta contem arquivos. Deseja apagar tambem a subpasta e esses arquivos?"
            delete_files = messagebox.askyesnocancel("Remover classe", message, parent=self.root)
            if delete_files is None:
                return
        else:
            confirmed = messagebox.askyesno("Remover classe", message, parent=self.root)
            if not confirmed:
                return
            delete_files = False

        remove_class_directory(
            self.output_dir,
            class_name,
            self.class_directories,
            delete_files=bool(delete_files),
            archive_files=has_files and not bool(delete_files),
        )
        self.classes = [name for name in self.classes if name != class_name]
        self.records = [record for record in self.records if record.class_name != class_name]
        self.undo_stack = [record for record in self.undo_stack if record.class_name != class_name]
        self._save_state()
        self._bind_shortcuts()
        self._update_status()
        self.info_var.set(f"Classe removida: {class_name}")
        self._focus_navigation_surface()
