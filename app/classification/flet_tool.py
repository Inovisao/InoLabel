"""Ferramenta de classificação de imagens com interface Flet."""

from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional

import flet as ft
from PIL import Image

from app.classification.dataset import (
    STATE_FILE_NAME,
    ClassificationRecord,
    add_class_directory,
    class_directory_has_files,
    classify_image_source,
    discover_images,
    export_classification_dataset,
    prepare_dataset,
    remove_class_directory,
)
from app.classification.tools.state import ClassificationStateMixin
from app.core.session import AnnotationSessionConfig
from app.ui.components.flet_components import (
    FletVar,
    danger_btn,
    neutral_btn,
    primary_btn,
    section_header,
)
from app.ui.file_manager import reveal_path
from app.ui.theme.flet_theme import COLORS, FONT, SIZES, SPACING
from app.ui.theme.palette import CLASS_COLORS


class FletClassificationTool(ClassificationStateMixin):
    """Ferramenta de classificação de imagens com interface Flet."""

    def __init__(self, *, session_config: AnnotationSessionConfig, page: ft.Page):
        self.page = page
        self.session_config = session_config
        self.data_root = session_config.data_root
        self.output_dir = session_config.output_dir
        self.classes = list(session_config.target_classes)
        self.move_files = False
        self.state_path = session_config.annotations_path or (self.output_dir / STATE_FILE_NAME)

        self.images = discover_images(self.data_root)
        if not self.images:
            self._show_error_and_exit(f"Nenhuma imagem válida encontrada em {self.data_root}")
            return
        self.source_image_count = len(self.images)

        self.class_directories = prepare_dataset(self.output_dir, self.classes)
        self.records: list[ClassificationRecord] = []
        self.undo_stack: list[ClassificationRecord] = []
        self.current_index = 0
        self.current_image: Optional[Image.Image] = None

        # FletVar proxies (compatível com mixins legados)
        self._info_text        = ft.Text("", size=FONT["body"], color=COLORS["muted"], expand=True)
        self._image_name_text  = ft.Text("", size=FONT["heading"], color=COLORS["text"], expand=True, no_wrap=True)
        self._current_class_text = ft.Text("", size=FONT["body"], color=COLORS["accent"])
        self._counter_text     = ft.Text("", size=FONT["caption"], color=COLORS["muted"])
        self._status_text      = ft.Text("", size=FONT["caption"], color=COLORS["muted"])

        self.info_var         = FletVar(self._info_text)
        self.image_name_var   = FletVar(self._image_name_text)
        self.current_class_var = FletVar(self._current_class_text)
        self.counter_var      = FletVar(self._counter_text)
        self.status_var       = FletVar(self._status_text)
        self.new_class_var    = FletVar()  # Sem controle vinculado — lido via .get()

        self._export_picker = ft.FilePicker(on_result=self._on_export_dir_picked)
        page.overlay.append(self._export_picker)

        self._load_existing_state()
        self._skip_classified_forward()
        self._build_ui()
        self._load_current_image()

    def run(self):
        pass  # Flet já rodando via ft.app()

    def finish_processing(self, message: str = ""):
        if message:
            print(f"[INFO] {message}")
        self.on_quit()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        page = self.page
        page.title = "InoLabel — Classificação"
        page.bgcolor = COLORS["bg"]
        page.padding = 0
        page.spacing = 0
        page.window.min_width = 800
        page.window.min_height = 500
        page.on_keyboard_event = self._on_page_keyboard_event

        self._canvas_image = ft.Image(
            src_base64="",
            fit=ft.ImageFit.CONTAIN,
            expand=True,
        )
        canvas_area = ft.Container(
            content=self._canvas_image,
            expand=True,
            bgcolor=COLORS["canvas_bg"],
            alignment=ft.alignment.center,
            padding=SPACING["md"],
        )

        self._classes_column = ft.Column(spacing=SPACING["xs"])
        self._new_class_field = ft.TextField(
            label="Nova classe",
            value="",
            on_change=lambda e: self.new_class_var.set(e.control.value),
            on_submit=lambda _: self.on_add_class(),
            height=44,
            text_size=FONT["body"],
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            bgcolor=COLORS["surface"],
            filled=True,
        )
        self._rebuild_class_list()

        sidebar = ft.Container(
            content=ft.ListView(
                controls=[
                    section_header("CLASSES"),
                    ft.Container(height=SPACING["xs"]),
                    self._classes_column,
                    ft.Container(height=SPACING["sm"]),
                    section_header("ADICIONAR CLASSE"),
                    ft.Container(height=SPACING["xs"]),
                    self._new_class_field,
                    ft.Container(height=SPACING["xs"]),
                    primary_btn("Adicionar", lambda _: self.on_add_class()),
                    ft.Container(height=SPACING["sm"]),
                    section_header("NAVEGAÇÃO"),
                    ft.Container(height=SPACING["xs"]),
                    neutral_btn("← Anterior", lambda _: self.on_previous_image()),
                    ft.Container(height=SPACING["xs"]),
                    neutral_btn("Próxima →", lambda _: self.on_skip()),
                    ft.Container(height=SPACING["xs"]),
                    neutral_btn("Desfazer  (Backspace)", lambda _: self.on_undo()),
                    ft.Container(height=SPACING["sm"]),
                    section_header("AÇÕES"),
                    ft.Container(height=SPACING["xs"]),
                    neutral_btn("Ver em pasta", lambda _: self.on_open_output_folder()),
                    ft.Container(height=SPACING["xs"]),
                    danger_btn("Remover imagem", lambda _: self.on_remove_current_image()),
                    ft.Container(height=SPACING["xs"]),
                    primary_btn("Exportar dataset", lambda _: self.on_export_dataset(), icon=ft.Icons.UPLOAD),
                    ft.Container(height=SPACING["sm"]),
                    ft.Divider(color=COLORS["border"], height=1),
                    ft.Container(height=SPACING["xs"]),
                    danger_btn("Sair  (Esc)", lambda _: self.on_quit(), icon=ft.Icons.LOGOUT),
                ],
                expand=True,
                spacing=0,
                padding=ft.padding.all(SPACING["sm"]),
            ),
            width=SIZES["sidebar_w"],
            bgcolor=COLORS["surface"],
            border=ft.border.only(left=ft.BorderSide(1, COLORS["border"])),
        )

        topbar = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[self._image_name_text, self._current_class_text],
                        spacing=2,
                        expand=True,
                    ),
                    self._counter_text,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACING["md"],
            ),
            bgcolor=COLORS["surface"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
            padding=ft.padding.symmetric(horizontal=SPACING["lg"], vertical=SPACING["sm"]),
            height=SIZES["topbar_h"],
        )

        statusbar = ft.Container(
            content=ft.Row(
                controls=[self._info_text, self._status_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACING["md"],
            ),
            bgcolor=COLORS["surface"],
            border=ft.border.only(top=ft.BorderSide(1, COLORS["border"])),
            padding=ft.padding.symmetric(horizontal=SPACING["lg"], vertical=0),
            height=SIZES["statusbar_h"],
        )

        page.controls = [
            ft.Column(
                controls=[
                    topbar,
                    ft.Row(
                        controls=[canvas_area, sidebar],
                        expand=True,
                        spacing=0,
                    ),
                    statusbar,
                ],
                expand=True,
                spacing=0,
            )
        ]

    # ── Class list ────────────────────────────────────────────────────────────

    def _rebuild_class_list(self):
        if not hasattr(self, "_classes_column"):
            return
        counts = self._counts_by_class() if self.records else {c: 0 for c in self.classes}
        rows: list[ft.Control] = []
        for idx, name in enumerate(self.classes):
            color = CLASS_COLORS[idx % len(CLASS_COLORS)]
            rows.append(self._class_row(idx, name, color, counts.get(name, 0)))
        self._classes_column.controls = rows
        if hasattr(self, "page"):
            self.page.update()

    def _class_row(self, idx: int, name: str, color: str, count: int) -> ft.Control:
        label = f"{idx + 1}  {name}  ({count})"

        def on_select(_e, n=name):
            self.on_class_selected(n)

        def on_remove(_e, n=name):
            self.on_remove_class(n)

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=4, height=40, bgcolor=color,
                        border_radius=ft.border_radius.only(top_left=4, bottom_left=4),
                    ),
                    ft.Container(width=SPACING["xs"]),
                    ft.ElevatedButton(
                        text=label,
                        on_click=on_select,
                        expand=True,
                        height=36,
                        style=ft.ButtonStyle(
                            bgcolor={ft.ControlState.DEFAULT: COLORS["primary"]},
                            color={ft.ControlState.DEFAULT: "#FFFFFF"},
                            padding=ft.padding.symmetric(horizontal=SPACING["sm"]),
                            shape=ft.RoundedRectangleBorder(radius=SIZES.get("radius_sm", 6)),
                        ),
                    ),
                    ft.Container(width=SPACING["xs"]),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=16,
                        icon_color=COLORS["danger"],
                        on_click=on_remove,
                        tooltip="Remover classe",
                        disabled=len(self.classes) <= 1,
                        style=ft.ButtonStyle(padding=4),
                    ),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=44,
            margin=ft.margin.only(bottom=SPACING["xs"]),
        )

    def _redraw_class_buttons(self):
        self._rebuild_class_list()

    # ── Image rendering ───────────────────────────────────────────────────────

    def _render_image(self):
        if self.current_image is None or not hasattr(self, "_canvas_image"):
            return
        image = self.current_image.copy()
        image.thumbnail((1200, 900), Image.Resampling.LANCZOS)
        buf = BytesIO()
        image.save(buf, format="JPEG", quality=88, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        self._canvas_image.src_base64 = b64
        self.page.update()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _skip_classified_forward(self):
        classified = self._classified_sources()
        while self.current_index < len(self.images) and self.images[self.current_index] in classified:
            self.current_index += 1

    def _display_path_for_source(self, source_path: Path) -> Path:
        if Path(source_path).exists():
            return source_path
        for record in reversed(self.records):
            if record.source_path == source_path and record.destination_path.exists():
                return record.destination_path
        return source_path

    def _load_current_image(self, *, skip_classified: bool = True):
        if skip_classified:
            self._skip_classified_forward()
        if self.current_index >= len(self.images):
            self.current_image = None
            if hasattr(self, "_canvas_image"):
                self._canvas_image.src_base64 = ""
            self.image_name_var.set("Classificação concluída")
            self.current_class_var.set("Use Exportar dataset para gerar as subpastas por classe.")
            self.counter_var.set(f"{len(self.records)}/{self.source_image_count} imagens")
            self.info_var.set(f"Dataset salvo em: {self.output_dir}")
            self._update_status()
            if hasattr(self, "page"):
                self.page.update()
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
        current_record = self._record_for_source(source_path)
        if current_record is None:
            self.current_class_var.set("Classe atual: ainda não selecionada")
        else:
            self.current_class_var.set(f"Classe atual: {current_record.class_name}")
        self.counter_var.set(f"{self.current_index + 1}/{len(self.images)}")
        self.info_var.set(str(image_path))
        self._update_status()
        self._render_image()

    def _update_status(self):
        counts = self._counts_by_class()
        parts = [f"{name}: {counts.get(name, 0)}" for name in self.classes]
        pending = max(0, len(self.images) - self.current_index)
        parts.append(f"Pendentes: {pending}")
        self.status_var.set(" | ".join(parts))
        self._rebuild_class_list()

    def on_skip(self):
        if self.current_index >= len(self.images):
            return
        self.current_index += 1
        self._load_current_image()

    def on_previous_image(self):
        if self.current_index <= 0:
            return
        self.current_index -= 1
        self._load_current_image(skip_classified=False)

    def on_undo(self):
        if not self.undo_stack:
            self.info_var.set("Nada para desfazer nesta sessão.")
            self.page.update()
            return
        record = self.undo_stack.pop()
        self.records = [item for item in self.records if item != record]
        try:
            self.current_index = self.images.index(record.source_path)
        except ValueError:
            self.current_index = max(0, self.current_index - 1)
        self._save_state()
        self.info_var.set(f"Desfeito: {record.source_path.name}")
        self._load_current_image(skip_classified=False)

    # ── Class actions (async dialogs) ─────────────────────────────────────────

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
            self._show_error(f"Falha ao classificar: {exc}")
            return
        if previous_record is not None:
            self._remove_previous_classification(previous_record)
        self.records.append(record)
        self.undo_stack.append(record)
        self._save_state()
        self.info_var.set(f"Associada a {class_name}: {source_path.name}")
        self.current_index += 1
        self._load_current_image()

    def on_add_class(self):
        class_name = self.new_class_var.get().strip()
        if not class_name:
            return
        if class_name in self.classes:
            self.info_var.set(f"Classe já existe: {class_name}")
            self.new_class_var.set("")
            if hasattr(self, "_new_class_field"):
                self._new_class_field.value = ""
            self.page.update()
            return
        add_class_directory(self.output_dir, class_name, self.class_directories)
        self.classes.append(class_name)
        self.new_class_var.set("")
        if hasattr(self, "_new_class_field"):
            self._new_class_field.value = ""
        self._save_state()
        self._update_status()
        self.info_var.set(f"Classe adicionada: {class_name}")
        self.page.update()

    def on_remove_class(self, class_name: str):
        if len(self.classes) <= 1:
            self.info_var.set("Mantenha ao menos uma classe.")
            self.page.update()
            return
        class_records = [r for r in self.records if r.class_name == class_name]
        has_files = class_directory_has_files(self.output_dir, class_name, self.class_directories)

        def do_remove(delete_files: bool):
            remove_class_directory(
                self.output_dir, class_name, self.class_directories,
                delete_files=delete_files,
                archive_files=has_files and not delete_files,
            )
            self.classes = [n for n in self.classes if n != class_name]
            self.records = [r for r in self.records if r.class_name != class_name]
            self.undo_stack = [r for r in self.undo_stack if r.class_name != class_name]
            self._save_state()
            self._update_status()
            self.info_var.set(f"Classe removida: {class_name}")
            self.page.update()

        msg = f'Remover a classe "{class_name}"?'
        if class_records:
            msg += f"\n\n{len(class_records)} registro(s) desta classe serão removidos."
        if has_files:
            msg += "\n\nA subpasta contém arquivos. Apagar também os arquivos?"
            self._show_confirm_dialog(
                "Remover classe",
                msg,
                confirm_text="Apagar arquivos",
                cancel_text="Manter arquivos",
                on_confirm=lambda: do_remove(True),
                on_cancel=lambda: do_remove(False),
            )
        else:
            self._show_confirm_dialog(
                "Remover classe",
                msg,
                on_confirm=lambda: do_remove(False),
            )

    # ── Dataset actions ───────────────────────────────────────────────────────

    def on_remove_current_image(self):
        if self.current_index >= len(self.images):
            return
        source_path = self.images[self.current_index]
        image_path = self._display_path_for_source(source_path)

        def do_remove():
            try:
                if image_path.exists():
                    image_path.unlink()
            except Exception as exc:  # pylint: disable=broad-except
                self._show_error(f"Falha ao remover imagem: {exc}")
                return
            self.records = [r for r in self.records if r.source_path != source_path]
            self.undo_stack = [r for r in self.undo_stack if r.source_path != source_path]
            self.images.pop(self.current_index)
            self.source_image_count = len(self.images)
            if self.current_index >= len(self.images):
                self.current_index = max(0, len(self.images) - 1)
            self._save_state()
            self.info_var.set(f"Imagem removida: {image_path.name}")
            self._load_current_image(skip_classified=False)

        self._show_confirm_dialog(
            "Remover imagem",
            f"Remover esta imagem do dataset e apagar o arquivo?\n\n{image_path}",
            on_confirm=do_remove,
        )

    def on_export_dataset(self):
        self._save_state()
        self._export_picker.get_directory_path(
            dialog_title="Selecione a pasta de destino do dataset",
        )

    def _on_export_dir_picked(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        export_root = self._resolve_export_dataset_path(Path(e.path))
        try:
            report = export_classification_dataset(
                records=self.records,
                classes=self.classes,
                class_directories=self.class_directories,
                dataset_root=export_root,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self._show_error(f"Falha ao exportar dataset: {exc}")
            return
        skipped = len(report["skipped"])
        message = f"Dataset exportado em: {report['dataset_root']} | {report['copied']} imagens"
        if skipped:
            message += f" | {skipped} ignorada(s)"
        self.info_var.set(message)
        self.page.update()
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
        try:
            self.page.window.close()
        except Exception:  # pylint: disable=broad-except
            pass

    def on_open_output_folder(self):
        if not reveal_path(self.output_dir):
            self.info_var.set(f"Não foi possível abrir: {self.output_dir}")
        self.page.update()

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def _on_page_keyboard_event(self, e: ft.KeyboardEvent):
        if getattr(self, "_ignore_keyboard", False):
            return
        key = e.key
        if key == "Escape":
            self.on_quit()
        elif key in ("Arrow Right", "ArrowRight", "d", "D"):
            self.on_skip()
        elif key in ("Arrow Left", "ArrowLeft", "a", "A"):
            self.on_previous_image()
        elif key == " " or key == "Space":
            self.on_skip()
        elif key == "Backspace":
            self.on_undo()
        elif key in "123456789":
            idx = int(key) - 1
            if 0 <= idx < len(self.classes):
                self.on_class_selected(self.classes[idx])

    # ── Dialog helpers ────────────────────────────────────────────────────────

    def _show_error(self, message: str):
        def close(_e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Erro"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=close)],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _show_error_and_exit(self, message: str):
        def close(_e):
            dlg.open = False
            self.page.update()
            try:
                self.page.window.close()
            except Exception:  # pylint: disable=broad-except
                pass

        dlg = ft.AlertDialog(
            title=ft.Text("Erro"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=close)],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _show_confirm_dialog(
        self,
        title: str,
        message: str,
        on_confirm: Callable,
        on_cancel: Optional[Callable] = None,
        confirm_text: str = "Confirmar",
        cancel_text: str = "Cancelar",
    ):
        def on_yes(_e):
            dlg.open = False
            self.page.update()
            on_confirm()

        def on_no(_e):
            dlg.open = False
            self.page.update()
            if on_cancel is not None:
                on_cancel()

        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton(confirm_text, on_click=on_yes),
                ft.TextButton(cancel_text, on_click=on_no),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
