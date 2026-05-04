"""Tkinter tool for manual image classification."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageTk

from app.classification.dataset import (
    STATE_FILE_NAME,
    ClassificationRecord,
    add_class_directory,
    class_directory_has_files,
    discover_images,
    load_state,
    prepare_dataset,
    remove_class_directory,
    transfer_image_to_class,
    write_state,
)
from app.core.session import AnnotationSessionConfig
from app.ui.file_manager import reveal_path
from app.ui.layout.responsive_window import apply_responsive_geometry
from app.ui.theme import COLORS, FONTS, SIZES, SPACING, install_scaled_theme


class ClassificationTool:
    """Manual image classification UI.

    Clicking a class copies the current source image into the class subfolder
    and advances to the next pending image.
    """

    def __init__(self, *, session_config: AnnotationSessionConfig):
        self.session_config = session_config
        self.data_root = session_config.data_root
        self.output_dir = session_config.output_dir
        self.classes = list(session_config.target_classes)
        self.move_files = bool(session_config.classification_move_files)
        self.state_path = session_config.annotations_path or (self.output_dir / STATE_FILE_NAME)

        self.root = tk.Tk()
        self.root.title("Classificacao de imagens")
        self.ui = install_scaled_theme(self.root)
        self.colors = self.ui["colors"]
        self.fonts = self.ui["fonts"]
        self.spacing = self.ui["spacing"]
        self.sizes = self.ui["sizes"]
        self.root.configure(bg=self.colors["bg"])
        apply_responsive_geometry(self.root, width_ratio=0.92, height_ratio=0.88)
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)

        self.images = discover_images(self.data_root)
        if not self.images:
            self.root.destroy()
            raise FileNotFoundError(f"Nenhuma imagem valida encontrada em {self.data_root}")
        self.source_image_count = len(self.images)

        self.class_directories = prepare_dataset(self.output_dir, self.classes)
        self.records: list[ClassificationRecord] = []
        self.undo_stack: list[ClassificationRecord] = []
        self.current_index = 0
        self.current_image: Image.Image | None = None
        self._photo = None
        self._render_retry_scheduled = False

        self.info_var = tk.StringVar(value="")
        self.counter_var = tk.StringVar(value="")
        self.image_name_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.new_class_var = tk.StringVar(value="")

        self._load_existing_state()
        self._filter_used_images()
        self._skip_classified_forward()
        self._build_ui()
        self._bind_shortcuts()
        self._load_current_image()

    def run(self):
        self.root.mainloop()

    def finish_processing(self, message: str = ""):
        if message:
            print(f"[INFO] {message}")
        self.on_quit()

    def _load_existing_state(self):
        state = load_state(self.state_path)
        if state is None:
            self._save_state()
            return
        if state.classes:
            self.classes = list(state.classes)
        if state.class_directories:
            self.class_directories = dict(state.class_directories)
            for dirname in self.class_directories.values():
                (self.output_dir / dirname).mkdir(parents=True, exist_ok=True)
        self.records = list(state.records)

    def _save_state(self):
        write_state(
            self.state_path,
            classes=self.classes,
            class_directories=self.class_directories,
            source_root=self.data_root,
            records=self.records,
        )

    def _filter_used_images(self):
        classified = self._classified_sources()
        filtered = []
        skipped = 0
        for image_path in self.images:
            if image_path in classified:
                skipped += 1
                continue
            filtered.append(image_path)
        self.images = filtered
        if skipped:
            self.info_var.set(f"{skipped} imagem(ns) ja usadas foram filtradas.")

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        topbar = tk.Frame(self.root, bg=self.colors["panel"], padx=self.spacing["lg"], pady=self.spacing["md"])
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.columnconfigure(0, weight=1)

        tk.Label(
            topbar,
            textvariable=self.image_name_var,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=self.fonts["heading"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            topbar,
            textvariable=self.counter_var,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=self.fonts["caption"],
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(self.spacing["lg"], 0))

        body = tk.Frame(self.root, bg=self.colors["bg"])
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=300)
        body.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, bg="#111827", highlightthickness=0)
        self.canvas.configure(takefocus=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self._render_image())

        sidebar = tk.Frame(body, bg=self.colors["panel"], padx=self.spacing["lg"], pady=self.spacing["lg"])
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        self.class_panel = tk.Frame(sidebar, bg=self.colors["panel"])
        self.class_panel.grid(row=0, column=0, sticky="ew")
        self._redraw_class_buttons()

        add_class_panel = tk.Frame(sidebar, bg=self.colors["panel"])
        add_class_panel.grid(row=1, column=0, sticky="ew", pady=(self.spacing["lg"], 0))
        add_class_panel.columnconfigure(0, weight=1)
        tk.Label(
            add_class_panel,
            text="Nova classe",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=self.fonts["label"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, self.spacing["xs"]))
        entry = tk.Entry(
            add_class_panel,
            textvariable=self.new_class_var,
            font=self.fonts["body"],
            bg=self.colors["input_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            bd=self.sizes["input_pad"],
        )
        entry.grid(row=1, column=0, sticky="ew", padx=(0, self.spacing["sm"]))
        entry.bind("<Return>", lambda _event: self.on_add_class())
        self._button(add_class_panel, "Adicionar", self.on_add_class, primary=True).grid(row=1, column=1, sticky="ew")

        controls = tk.Frame(sidebar, bg=self.colors["panel"])
        controls.grid(row=2, column=0, sticky="ew", pady=(self.spacing["lg"], 0))
        controls.columnconfigure(0, weight=1)
        nav = tk.Frame(controls, bg=self.colors["panel"])
        nav.grid(row=0, column=0, sticky="ew", pady=(0, self.spacing["sm"]))
        nav.columnconfigure(0, weight=1)
        nav.columnconfigure(1, weight=1)
        self._button(nav, "Anterior", self.on_previous_image).grid(row=0, column=0, sticky="ew", padx=(0, self.spacing["xs"]))
        self._button(nav, "Proxima", self.on_skip).grid(row=0, column=1, sticky="ew", padx=(self.spacing["xs"], 0))
        self._button(controls, "Desfazer (backspace)", self.on_undo).grid(row=1, column=0, sticky="ew", pady=(0, self.spacing["sm"]))
        self._button(controls, "Ver em folder", self.on_open_output_folder).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, self.spacing["sm"]),
        )
        self._button(controls, "Sair", self.on_quit, danger=True).grid(row=3, column=0, sticky="ew")

        tk.Label(
            sidebar,
            textvariable=self.status_var,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=self.fonts["caption"],
            justify=tk.LEFT,
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", pady=(self.spacing["lg"], 0))

        statusbar = tk.Label(
            self.root,
            textvariable=self.info_var,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=self.fonts["caption"],
            anchor="w",
            padx=self.spacing["lg"],
            pady=self.spacing["sm"],
        )
        statusbar.grid(row=2, column=0, sticky="ew")

    def _button(self, parent, text: str, command, *, primary: bool = False, danger: bool = False):
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=self.fonts["button"],
            padx=self.sizes["btn_pad_x"],
            pady=self.sizes["btn_pad_y"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            highlightthickness=0,
        )
        if danger:
            button.configure(
                bg=self.colors["danger"],
                fg=COLORS["fg_light"],
                activebackground=self.colors["danger"],
                activeforeground=COLORS["fg_light"],
            )
        elif primary:
            button.configure(
                bg=self.colors["primary"],
                fg=COLORS["fg_light"],
                activebackground=self.colors["primary_active"],
                activeforeground=COLORS["fg_light"],
            )
        else:
            button.configure(
                bg=self.colors["neutral"],
                fg=self.colors["text"],
                activebackground=self.colors["neutral_active"],
                activeforeground=self.colors["text"],
            )
        return button

    def _redraw_class_buttons(self):
        for child in self.class_panel.winfo_children():
            child.destroy()
        counts = self._counts_by_class()
        for idx, class_name in enumerate(self.classes):
            row = tk.Frame(self.class_panel, bg=self.colors["panel"])
            row.pack(fill=tk.X, pady=(0, self.spacing["sm"]))
            row.columnconfigure(0, weight=1)
            label = f"{idx + 1}  {class_name}  ({counts.get(class_name, 0)})"
            self._button(
                row,
                label,
                lambda name=class_name: self.on_class_selected(name),
                primary=True,
            ).grid(row=0, column=0, sticky="ew", padx=(0, self.spacing["xs"]))
            remove_state = tk.NORMAL if len(self.classes) > 1 else tk.DISABLED
            remove_btn = self._button(row, "Remover", lambda name=class_name: self.on_remove_class(name), danger=True)
            remove_btn.config(state=remove_state)
            remove_btn.grid(row=0, column=1, sticky="e")

    def _bind_shortcuts(self):
        for idx in range(1, 10):
            self.root.unbind_all(str(idx))
            self.root.unbind_all(f"<KP_{idx}>")
        for idx, class_name in enumerate(self.classes[:9], start=1):
            self.root.bind_all(str(idx), lambda event, name=class_name: self._run_shortcut(event, lambda: self.on_class_selected(name)))
            self.root.bind_all(f"<KP_{idx}>", lambda event, name=class_name: self._run_shortcut(event, lambda: self.on_class_selected(name)))
        for key in ("<Right>", "<Down>", "d", "D", "s", "S"):
            self.root.bind_all(key, lambda event: self._run_shortcut(event, self.on_skip))
        for key in ("<Left>", "<Up>", "a", "A", "w", "W"):
            self.root.bind_all(key, lambda event: self._run_shortcut(event, self.on_previous_image))
        self.root.bind_all("<space>", lambda event: self._run_shortcut(event, self.on_skip))
        self.root.bind_all("<BackSpace>", lambda event: self._run_shortcut(event, self.on_undo))
        self.root.bind_all("<Escape>", lambda event: self._run_shortcut(event, self.on_quit))

    def _run_shortcut(self, event, action):
        if isinstance(getattr(event, "widget", None), (tk.Entry, tk.Text)):
            return
        action()

    def _focus_navigation_surface(self):
        try:
            self.canvas.focus_set()
        except tk.TclError:
            self.root.focus_set()

    def _counts_by_class(self) -> dict[str, int]:
        counts = {class_name: 0 for class_name in self.classes}
        for record in self.records:
            counts[record.class_name] = counts.get(record.class_name, 0) + 1
        return counts

    def _classified_sources(self) -> set[Path]:
        return {record.source_path for record in self.records}

    def _skip_classified_forward(self):
        classified = self._classified_sources()
        while self.current_index < len(self.images) and self.images[self.current_index] in classified:
            self.current_index += 1

    def _load_current_image(self, *, skip_classified: bool = True):
        if skip_classified:
            self._skip_classified_forward()
        if self.current_index >= len(self.images):
            self.current_image = None
            self.canvas.delete("all")
            self.image_name_var.set("Classificacao concluida")
            self.counter_var.set(f"{len(self.records)}/{self.source_image_count} imagens")
            self.info_var.set(f"Dataset salvo em: {self.output_dir}")
            self._update_status()
            return

        source_path = self.images[self.current_index]
        image_path = self._display_path_for_source(source_path)
        try:
            self.current_image = Image.open(image_path).convert("RGB")
        except Exception as exc:  # pylint: disable=broad-except
            self.info_var.set(f"Falha ao abrir {image_path.name}: {exc}")
            self.current_index += 1
            self._load_current_image()
            return
        self.image_name_var.set(image_path.name)
        self.counter_var.set(f"{self.current_index + 1}/{len(self.images)}")
        self.info_var.set(str(image_path))
        self._update_status()
        self._render_image()
        self._focus_navigation_surface()

    def _display_path_for_source(self, source_path: Path) -> Path:
        if Path(source_path).exists():
            return source_path
        for record in reversed(self.records):
            if record.source_path == source_path and record.destination_path.exists():
                return record.destination_path
        return source_path

    def _record_for_source(self, source_path: Path) -> ClassificationRecord | None:
        for record in reversed(self.records):
            if record.source_path == source_path:
                return record
        return None

    def _render_image(self):
        if self.current_image is None:
            return
        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        if canvas_w <= 2 or canvas_h <= 2:
            if not self._render_retry_scheduled:
                self._render_retry_scheduled = True
                self.root.after(50, self._retry_render_image)
            return
        self._render_retry_scheduled = False
        image = self.current_image.copy()
        target_w = max(1, canvas_w - 24)
        target_h = max(1, canvas_h - 24)
        image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        x = canvas_w // 2
        y = canvas_h // 2
        self.canvas.create_image(x, y, image=self._photo, anchor=tk.CENTER)

    def _retry_render_image(self):
        self._render_retry_scheduled = False
        self._render_image()

    def _update_status(self):
        counts = self._counts_by_class()
        lines = [f"{class_name}: {counts.get(class_name, 0)}" for class_name in self.classes]
        pending = max(0, len(self.images) - self.current_index)
        operation = "Mover" if self.move_files else "Copiar"
        lines.append(f"Acao: {operation}")
        lines.append(f"Pendentes: {pending}")
        lines.append(f"Dataset: {self.output_dir.name}")
        self.status_var.set("\n".join(lines))
        if hasattr(self, "class_panel"):
            self._redraw_class_buttons()

    def on_class_selected(self, class_name: str):
        if self.current_index >= len(self.images):
            return
        source_path = self.images[self.current_index]
        previous_record = self._record_for_source(source_path)
        image_path = source_path
        if previous_record is not None and not image_path.exists():
            image_path = previous_record.destination_path
        try:
            record = transfer_image_to_class(
                image_path,
                class_name=class_name,
                output_dir=self.output_dir,
                class_directories=self.class_directories,
                move=self.move_files,
            )
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Falha ao classificar", str(exc), parent=self.root)
            return
        if previous_record is not None:
            self._remove_previous_classification(previous_record, replacement=record)
            record = ClassificationRecord(
                source_path=source_path,
                destination_path=record.destination_path,
                class_name=record.class_name,
                classified_at=record.classified_at,
                operation=record.operation,
            )
        self.records.append(record)
        self.undo_stack.append(record)
        self._save_state()
        action = "Movida" if record.operation == "move" else "Copiada"
        self.info_var.set(f"{action} para {class_name}: {record.destination_path.name}")
        self.current_index += 1
        self._load_current_image()
        self._focus_navigation_surface()

    def _remove_previous_classification(self, record: ClassificationRecord, *, replacement: ClassificationRecord):
        self.records = [item for item in self.records if item != record]
        self.undo_stack = [item for item in self.undo_stack if item != record]
        if record.destination_path == replacement.destination_path:
            return
        try:
            if record.destination_path.exists():
                record.destination_path.unlink()
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[AVISO] Falha ao remover classificacao anterior: {record.destination_path} | {exc}")

    def on_skip(self):
        if self.current_index >= len(self.images):
            return
        self.current_index += 1
        self._load_current_image()
        self._focus_navigation_surface()

    def on_previous_image(self):
        if self.current_index <= 0:
            return
        self.current_index -= 1
        self._load_current_image(skip_classified=False)
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

    def on_undo(self):
        if not self.undo_stack:
            self.info_var.set("Nada para desfazer nesta sessao.")
            return
        record = self.undo_stack.pop()
        try:
            if record.operation == "move" and record.destination_path.exists() and not record.source_path.exists():
                record.source_path.parent.mkdir(parents=True, exist_ok=True)
                record.destination_path.replace(record.source_path)
            elif record.destination_path.exists():
                record.destination_path.unlink()
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Falha ao desfazer", str(exc), parent=self.root)
            return
        self.records = [item for item in self.records if item != record]
        try:
            self.current_index = self.images.index(record.source_path)
        except ValueError:
            self.current_index = max(0, self.current_index - 1)
        self._save_state()
        self.info_var.set(f"Desfeito: {record.destination_path.name}")
        self._load_current_image(skip_classified=False)
        self._focus_navigation_surface()

    def on_quit(self):
        self._save_state()
        self.root.destroy()

    def on_open_output_folder(self):
        if not reveal_path(self.output_dir):
            self.info_var.set(f"Nao foi possivel abrir: {self.output_dir}")
