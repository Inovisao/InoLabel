"""Wizard de inicialização em Flet — 4 passos: modo → dataset → estado → modelo/classes."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, List, Optional

import flet as ft

from app.classification.dataset import (
    STATE_FILE_NAME as CLASSIFICATION_STATE_FILE_NAME,
    discover_images,
    latest_output_state_for_sources as latest_classification_state_for_sources,
    list_output_states_for_sources as list_classification_states_for_sources,
    load_required_state as load_classification_state,
)
from app.config import DATA_ROOT, LOGO_PATH, WEIGHTS_PATH
from app.core.output_state import (
    ANNOTATION_FILE_NAMES,
    OutputState,
    create_new_output_dir,
    find_annotations_path,
    latest_output_state_for_sources,
    list_output_states_for_sources,
    load_annotation_state,
)
from app.core.session import AnnotationSessionConfig, AnnotationTaskMode, normalize_class_names
from app.core.startup_cache import load_startup_cache, save_startup_cache
from app.sources.discovery import SourceDiscoveryService, SourceSummary
from app.ui.components.flet_components import (
    FletVar, accent_btn, badge, caption_text, card, class_tag,
    danger_btn, ghost_btn, hdivider, icon_btn, label_text,
    neutral_btn, primary_btn, section_header, surface, text_field,
)
from app.ui.theme.flet_theme import COLORS, FONT, SIZES, SPACING
from app.ui.theme.palette import CLASS_COLORS


def ask_startup_config_flet(page: ft.Page, on_complete: Callable[[Optional[AnnotationSessionConfig]], None]) -> None:
    wizard = FletStartupWizard(page, on_complete)
    wizard.show()


# ─────────────────────────────────────────────────────────────────────────────

class FletStartupWizard:
    def __init__(self, page: ft.Page, on_complete: Callable[[Optional[AnnotationSessionConfig]], None]):
        self.page = page
        self.on_complete = on_complete

        # ── Pickers
        self.folder_picker = ft.FilePicker(on_result=self._on_folder_picked)
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self.model_picker = ft.FilePicker(on_result=self._on_model_picked)
        self.state_picker = ft.FilePicker(on_result=self._on_state_picked)
        page.overlay.extend([self.folder_picker, self.file_picker, self.model_picker, self.state_picker])

        # ── Estado
        cache = load_startup_cache()
        self.discovery = SourceDiscoveryService()
        self.result: Optional[AnnotationSessionConfig] = None

        self.mode: AnnotationTaskMode = cache.mode or AnnotationTaskMode.TRACKING
        self.data_root_str: str = self._initial_path(cache.data_root, DATA_ROOT)
        self.weights_paths: List[str] = [str(p) for p in cache.weights_paths] if cache.weights_paths else (
            [str(WEIGHTS_PATH)] if Path(WEIGHTS_PATH).exists() else []
        )
        self.classes: List[str] = []
        self.loaded_state_categories: tuple[dict, ...] = ()
        self.output_state_mode: str = "new"
        self.selected_state_path: Optional[Path] = None
        self.output_state_status: str = ""
        self.model_status: str = "Nenhum modelo validado."
        self.summary: Optional[SourceSummary] = None
        self.output_states: list[OutputState] = []

        # Diálogo de alerta reutilizável (instanciado sob demanda para compatibilidade de API)
        self._alert: Optional[ft.AlertDialog] = None

    @staticmethod
    def _initial_path(cached: Optional[Path], fallback) -> str:
        if cached is not None:
            return str(cached)
        fb = Path(fallback)
        return str(fb) if fb.exists() else ""

    # ── Navegação ──────────────────────────────────────────────────────────────

    def show(self):
        self.show_mode_screen()

    def _set_page(self, controls: list[ft.Control]):
        self.page.controls.clear()
        self.page.controls.extend(controls)
        self.page.update()

    # ── Shell visual ───────────────────────────────────────────────────────────

    def _logo_bar(self) -> ft.Control:
        logo_row_controls: list[ft.Control] = []
        if LOGO_PATH.exists():
            try:
                logo_row_controls.append(
                    ft.Image(src=str(LOGO_PATH), width=80, height=32, fit=ft.ImageFit.CONTAIN)
                )
            except Exception:  # pylint: disable=broad-except
                pass
        logo_row_controls += [
            ft.Text("InoLabel", size=FONT["heading"], weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
            ft.Container(expand=True),
            ft.Text("Inovisão", size=FONT["caption"], color=COLORS["accent"]),
        ]
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(controls=logo_row_controls, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=SPACING["sm"]),
                    padding=ft.padding.symmetric(horizontal=SPACING["xl"], vertical=SPACING["sm"]),
                ),
                ft.Container(height=2, bgcolor=COLORS["accent"]),
            ],
            spacing=0,
        )

    def _step_indicator(self, current: int) -> ft.Control:
        is_classification = self.mode is AnnotationTaskMode.CLASSIFICATION
        steps = ["Modo", "Imagens" if is_classification else "Dataset", "Estado", "Classes" if is_classification else "Modelo"]
        items: list[ft.Control] = []
        for i, label in enumerate(steps, 1):
            is_done = i < current
            is_active = i == current

            if is_done:
                circle_bg, circle_fg = COLORS["primary"], COLORS["on_primary"]
                lbl_color = COLORS["text"]
                circle_content: ft.Control = ft.Icon(ft.Icons.CHECK, size=12, color=circle_fg)
            elif is_active:
                circle_bg, circle_fg = COLORS["accent"], COLORS["on_accent"]
                lbl_color = COLORS["text"]
                circle_content = ft.Text(str(i), size=FONT["caption"], weight=ft.FontWeight.BOLD, color=circle_fg)
            else:
                circle_bg, circle_fg = COLORS["neutral"], COLORS["muted"]
                lbl_color = COLORS["muted"]
                circle_content = ft.Text(str(i), size=FONT["caption"], color=circle_fg)

            items.append(
                ft.Row(
                    controls=[
                        ft.Container(
                            content=circle_content,
                            width=24, height=24,
                            bgcolor=circle_bg,
                            border_radius=12,
                            alignment=ft.alignment.center,
                        ),
                        ft.Text(label, size=FONT["caption"], weight=ft.FontWeight.W_500, color=lbl_color),
                    ],
                    spacing=SPACING["xs"],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
            if i < len(steps):
                items.append(
                    ft.Container(
                        width=28, height=2,
                        bgcolor=COLORS["primary"] if is_done else COLORS["border"],
                    )
                )
        return ft.Container(
            content=ft.Row(controls=items, spacing=SPACING["xs"], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=SPACING["xl"], vertical=SPACING["md"]),
        )

    def _screen_layout(
        self,
        step: int,
        title: str,
        subtitle: str,
        body: ft.Control,
        back_cb: Optional[Callable],
        next_cb: Callable,
        next_text: str = "Continuar",
    ) -> list[ft.Control]:
        footer_controls: list[ft.Control] = [ft.Container(expand=True)]
        if back_cb:
            footer_controls.append(neutral_btn("Voltar", lambda _: back_cb(), expand=False))
        footer_controls.append(primary_btn(next_text, lambda _: next_cb(), expand=False))

        content = ft.Column(
            controls=[
                ft.Text(title, size=FONT["title"], weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                ft.Container(height=SPACING["xs"]),
                ft.Text(subtitle, size=FONT["body"], color=COLORS["muted"]),
                ft.Container(height=SPACING["lg"]),
                body,
                ft.Container(height=SPACING["xl"]),
                ft.Row(controls=footer_controls, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=SPACING["sm"]),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )

        return [
            ft.Column(
                controls=[
                    self._logo_bar(),
                    self._step_indicator(step),
                    ft.Container(
                        content=content,
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=SPACING["xl"], vertical=SPACING["md"]),
                        alignment=ft.alignment.top_center,
                    ),
                ],
                expand=True,
                spacing=0,
            )
        ]

    # ── Tela 1: Modo ───────────────────────────────────────────────────────────

    def show_mode_screen(self):
        self._set_page(self._screen_layout(
            step=1,
            title="Escolha o fluxo de anotação",
            subtitle="Defina se esta sessão vai manter identidade dos objetos ou gerar anotações independentes.",
            body=self._mode_cards(),
            back_cb=None,
            next_cb=self.show_dataset_screen,
        ))

    def _mode_cards(self) -> ft.Control:
        modes = [
            (AnnotationTaskMode.TRACKING,      ft.Icons.TRACK_CHANGES,  "Tracking",       "Mantém IDs por objeto com rastreamento multiclass."),
            (AnnotationTaskMode.DETECTION,     ft.Icons.SEARCH,          "Detection",      "Gera caixas independentes, sem IDs de rastreamento."),
            (AnnotationTaskMode.OBB,           ft.Icons.CROP_ROTATE,     "OBB",            "Caixas orientadas com ângulo — exportação YOLO OBB."),
            (AnnotationTaskMode.CLASSIFICATION,ft.Icons.LABEL,           "Classification", "Copia imagens para subpastas por classe selecionada."),
        ]
        cards = [self._mode_card(m, icon, label, desc) for m, icon, label, desc in modes]
        return ft.Row(controls=cards, spacing=SPACING["md"], expand=True)

    def _mode_card(self, mode: AnnotationTaskMode, icon: str, label: str, desc: str) -> ft.Control:
        is_selected = self.mode is mode

        def select(_e):
            self.mode = mode
            self.show_mode_screen()

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(icon, size=20, color=COLORS["primary"] if is_selected else COLORS["muted"]),
                            ft.Text(label, size=FONT["subhead"], weight=ft.FontWeight.W_600,
                                    color=COLORS["text"] if is_selected else COLORS["muted"]),
                        ],
                        spacing=SPACING["sm"],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(desc, size=FONT["caption"], color=COLORS["muted"]),
                ],
                spacing=SPACING["sm"],
            ),
            bgcolor=COLORS["primary_muted"] if is_selected else COLORS["surface"],
            border=ft.border.all(2 if is_selected else 1, COLORS["primary"] if is_selected else COLORS["border"]),
            border_radius=SIZES["radius"],
            padding=SPACING["md"],
            expand=True,
            on_click=select,
            ink=True,
        )

    # ── Tela 2: Dataset ────────────────────────────────────────────────────────

    def show_dataset_screen(self):
        is_classification = self.mode is AnnotationTaskMode.CLASSIFICATION

        self._data_field = text_field(
            label="Caminho da fonte",
            value=self.data_root_str,
            on_change=lambda e: setattr(self, "data_root_str", e.control.value),
            on_submit=lambda _: self._validate_dataset_and_continue(),
        )

        summary_text = self._build_summary_text()

        body = ft.Column(
            controls=[
                card(
                    ft.Column(
                        controls=[
                            label_text("Fonte de dados"),
                            ft.Container(height=SPACING["sm"]),
                            self._data_field,
                            ft.Container(height=SPACING["sm"]),
                            ft.Row(
                                controls=[
                                    ft.Container(expand=True),
                                    neutral_btn("Selecionar pasta", lambda _: self.folder_picker.get_directory_path(), expand=False),
                                    neutral_btn("Selecionar arquivo", lambda _: self.file_picker.pick_files(
                                        allowed_extensions=["mp4","avi","mov","mkv","jpg","jpeg","png","bmp","tif","tiff","txt","lst"],
                                    ), expand=False),
                                ],
                                spacing=SPACING["sm"],
                            ),
                            ft.Container(height=SPACING["sm"]),
                            caption_text(summary_text),
                        ],
                        spacing=0,
                    )
                ),
            ],
            spacing=SPACING["md"],
        )

        self._set_page(self._screen_layout(
            step=2,
            title="Importe o dataset" if is_classification else "Importe o dataset",
            subtitle="Selecione uma pasta, vídeo, imagem única ou lista de imagens.",
            body=body,
            back_cb=self.show_mode_screen,
            next_cb=self._validate_dataset_and_continue,
        ))

    def _on_folder_picked(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.data_root_str = e.path
            self.summary = None
            self.show_dataset_screen()

    def _on_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.data_root_str = e.files[0].path
            self.summary = None
            self.show_dataset_screen()

    def _build_summary_text(self) -> str:
        if self.summary is None:
            return "Nenhuma fonte validada ainda."
        return (
            f"✓  {self.summary.total} fonte(s) — "
            f"vídeos: {self.summary.video_count}  "
            f"imagens: {self.summary.image_count}  "
            f"listas: {self.summary.image_list_count}"
        )

    def _validate_dataset_and_continue(self):
        raw = self.data_root_str.strip()
        if not raw:
            self._alert_error("Dataset inválido", "Selecione uma fonte de dados antes de continuar.")
            return
        data_root = Path(raw).expanduser()
        if not data_root.exists():
            self._alert_error("Dataset inválido", f"Fonte não encontrada:\n{data_root}")
            return
        self.summary = self.discovery.summarize(data_root)
        if not self.summary.has_sources:
            self._alert_error("Dataset inválido", f"Nenhuma fonte válida encontrada em:\n{data_root}")
            return
        if self.mode is AnnotationTaskMode.CLASSIFICATION:
            if not discover_images(data_root):
                self._alert_error("Dataset inválido", f"Nenhuma imagem encontrada em:\n{data_root}")
                return
        self.show_state_screen()

    # ── Tela 3: Estado ─────────────────────────────────────────────────────────

    def show_state_screen(self):
        is_classification = self.mode is AnnotationTaskMode.CLASSIFICATION
        sources = self._current_project_sources()
        if is_classification:
            self.output_states = list_classification_states_for_sources(sources) if sources else []
        else:
            self.output_states = list_output_states_for_sources(sources) if sources else []
        latest = self.output_states[-1] if self.output_states else None

        if latest is not None and self.output_state_mode == "new" and self.selected_state_path is None:
            self.output_state_mode = "resume_latest"
            self.selected_state_path = latest.state_path if is_classification else latest.annotations_path
            self.output_state_status = f"Último estado: {latest.label}"
            self._apply_state_template(self.selected_state_path)

        options = [
            ("resume_latest",  "Continuar último estado",          latest.label if latest else "Nenhum estado anterior.",     latest is not None),
            ("template_latest","Usar último como modelo",           "Carrega classes/config e cria output novo.",               latest is not None),
            ("manual",         "Escolher arquivo manualmente",      "Permite continuar ou usar como modelo qualquer estado.",  True),
            ("new",            "Criar novo estado",                 "Cria pasta em outputs/ com task e data/hora.",            True),
        ]

        option_cards = [self._state_option_card(*o) for o in options]

        body = ft.Column(
            controls=[
                card(
                    ft.Column(
                        controls=[
                            *option_cards,
                            hdivider(),
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=caption_text(self.output_state_status or "Selecione um estado acima."),
                                        expand=True,
                                    ),
                                    neutral_btn("Selecionar arquivo", lambda _: self.state_picker.pick_files(
                                        allowed_extensions=["json"],
                                    ), expand=False),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=SPACING["sm"],
                            ),
                        ],
                        spacing=SPACING["sm"],
                    )
                )
            ]
        )

        self._set_page(self._screen_layout(
            step=3,
            title="Escolha o estado de saída",
            subtitle="Continue um output existente, use como modelo ou comece do zero.",
            body=body,
            back_cb=self.show_dataset_screen,
            next_cb=self.show_model_screen,
        ))

    def _state_option_card(self, value: str, title: str, desc: str, enabled: bool) -> ft.Control:
        is_selected = self.output_state_mode == value

        def select(_e):
            if not enabled:
                return
            self.output_state_mode = value
            self._on_state_mode_changed(value)
            self.show_state_screen()

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.RADIO_BUTTON_CHECKED if is_selected else ft.Icons.RADIO_BUTTON_OFF,
                            size=18,
                            color=COLORS["primary"] if is_selected else (COLORS["muted"] if enabled else COLORS["disabled"]),
                        ),
                        width=28,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(title, size=FONT["label"], weight=ft.FontWeight.W_500,
                                    color=COLORS["text"] if enabled else COLORS["disabled"]),
                            ft.Text(desc, size=FONT["caption"], color=COLORS["muted"] if enabled else COLORS["disabled"]),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            bgcolor=COLORS["primary_muted"] if is_selected else ft.Colors.TRANSPARENT,
            border_radius=SIZES["radius_sm"],
            padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
            on_click=select if enabled else None,
            ink=enabled,
        )

    def _on_state_mode_changed(self, value: str):
        is_classification = self.mode is AnnotationTaskMode.CLASSIFICATION
        if value in {"resume_latest", "template_latest"}:
            if is_classification:
                latest = latest_classification_state_for_sources(self._current_project_sources())
                self.selected_state_path = latest.state_path if latest else None
            else:
                latest = latest_output_state_for_sources(self._current_project_sources())
                self.selected_state_path = latest.annotations_path if latest else None
            if latest:
                self.output_state_status = f"Estado selecionado: {latest.label}"
                self._apply_state_template(self.selected_state_path)
            else:
                self.output_state_mode = "new"
                self.classes = []
                self.loaded_state_categories = ()
                self.output_state_status = "Nenhum estado salvo encontrado."
        elif value == "new":
            self.selected_state_path = None
            self.classes = []
            self.loaded_state_categories = ()
            self.output_state_status = "Novo estado será criado ao iniciar."

    def _on_state_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        path = Path(e.files[0].path).expanduser()
        is_classification = self.mode is AnnotationTaskMode.CLASSIFICATION
        if is_classification:
            if path.name != CLASSIFICATION_STATE_FILE_NAME:
                self._alert_error("Estado inválido", f"Selecione um arquivo {CLASSIFICATION_STATE_FILE_NAME}.")
                return
            try:
                state = load_classification_state(path)
            except Exception as exc:
                self._alert_error("Estado inválido", str(exc))
                return
            if not state.classes:
                self._alert_error("Estado inválido", "O arquivo não possui classes.")
                return
            self.selected_state_path = path
            self.output_state_mode = "manual"
            self.classes = list(state.classes)
            self.output_state_status = f"Selecionado: {path.name} — {len(state.classes)} classes"
        else:
            if path.name == CLASSIFICATION_STATE_FILE_NAME:
                self._alert_error("Estado inválido", "Use annotations.coco.json para detecção/OBB.")
                return
            if find_annotations_path(path) is None:
                self._alert_error("Estado inválido", "Selecione um COCO válido: annotations.coco.json.")
                return
            try:
                state = load_annotation_state(path)
            except Exception as exc:
                self._alert_error("Estado inválido", str(exc))
                return
            if not state.class_names:
                self._alert_error("Estado inválido", "O arquivo não possui classes.")
                return
            self.selected_state_path = state.annotations_path
            self.output_state_mode = "manual"
            self.classes = list(state.class_names)
            self.loaded_state_categories = state.categories
            self._sync_categories()
            self.output_state_status = f"Selecionado: {path.name} — {len(state.class_names)} classes"
        self.show_state_screen()

    def _apply_state_template(self, annotations_path: Optional[Path]) -> bool:
        if annotations_path is None:
            return False
        is_classification = self.mode is AnnotationTaskMode.CLASSIFICATION
        try:
            if is_classification:
                state = load_classification_state(annotations_path)
                self.classes = list(state.classes)
                self.loaded_state_categories = ()
            else:
                state = load_annotation_state(annotations_path)
                self.classes = list(state.class_names)
                self.loaded_state_categories = state.categories
                self._sync_categories()
                if state.task_mode is not None:
                    self.mode = state.task_mode
        except Exception:  # pylint: disable=broad-except
            return False
        return True

    # ── Tela 4: Modelo / Classes ───────────────────────────────────────────────

    def show_model_screen(self):
        is_classification = self.mode is AnnotationTaskMode.CLASSIFICATION

        model_section: list[ft.Control] = []
        if not is_classification:
            model_rows = [self._model_row(i, p) for i, p in enumerate(self.weights_paths)]
            if not model_rows:
                model_rows = [caption_text("Nenhum modelo adicionado.")]
            model_section = [
                label_text("Modelos (.pt)"),
                ft.Container(height=SPACING["xs"]),
                ft.Column(controls=model_rows, spacing=SPACING["xs"]),
                ft.Container(height=SPACING["sm"]),
                ft.Row(
                    controls=[
                        ft.Container(expand=True),
                        neutral_btn("Adicionar modelo(s)", lambda _: self.model_picker.pick_files(
                            allow_multiple=True,
                            allowed_extensions=["pt"],
                        ), expand=False),
                        neutral_btn("Validar modelos", lambda _: self._validate_models(), expand=False),
                    ],
                    spacing=SPACING["sm"],
                ),
                ft.Container(height=SPACING["sm"]),
                caption_text(self.model_status),
                hdivider(),
            ]

        class_rows = [self._class_row(i, name) for i, name in enumerate(self.classes)]
        if not class_rows:
            class_rows = [caption_text("Nenhuma classe adicionada.")]

        add_class_field = text_field(hint="Nova classe...", expand=True)

        def _add_class(_e):
            name = add_class_field.value.strip()
            if name and name not in self.classes:
                self.classes.append(name)
                self._sync_categories()
            add_class_field.value = ""
            self.show_model_screen()

        class_section: list[ft.Control] = [
            label_text("Classes"),
            ft.Container(height=SPACING["xs"]),
            ft.Column(controls=class_rows, spacing=SPACING["xs"]),
            ft.Container(height=SPACING["sm"]),
            ft.Row(
                controls=[
                    add_class_field,
                    primary_btn("+ Adicionar", _add_class, expand=False),
                ],
                spacing=SPACING["sm"],
            ),
        ]

        body = card(
            ft.Column(
                controls=[
                    *model_section,
                    *class_section,
                    ft.Container(height=SPACING["sm"]),
                    caption_text(
                        f"Modo: {self.mode.label}  ·  {self._build_summary_text()}"
                    ),
                ],
                spacing=SPACING["xs"],
                scroll=ft.ScrollMode.AUTO,
            )
        )

        next_text = "Iniciar classificação" if is_classification else "Iniciar anotação"
        self._set_page(self._screen_layout(
            step=4,
            title="Defina as classes" if is_classification else "Modelos e classes",
            subtitle="Adicione os pesos YOLO e configure as classes para a sessão.",
            body=body,
            back_cb=self.show_state_screen,
            next_cb=self._finish,
            next_text=next_text,
        ))

    def _model_row(self, idx: int, path_str: str) -> ft.Control:
        name = Path(path_str).name

        def remove(_e):
            self.weights_paths.pop(idx)
            self.show_model_screen()

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.MODEL_TRAINING, size=14, color=COLORS["muted"]),
                    ft.Text(name, size=FONT["body"], color=COLORS["text"], expand=True),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=14,
                        icon_color=COLORS["danger"],
                        on_click=remove,
                        tooltip="Remover",
                        style=ft.ButtonStyle(padding=4),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACING["xs"],
            ),
            bgcolor=COLORS["surface_alt"],
            border_radius=SIZES["radius_sm"],
            padding=ft.padding.symmetric(horizontal=SPACING["sm"], vertical=SPACING["xs"]),
        )

    def _class_row(self, idx: int, name: str) -> ft.Control:
        color = CLASS_COLORS[idx % len(CLASS_COLORS)]

        def move_up(_e):
            if idx > 0:
                self.classes[idx], self.classes[idx - 1] = self.classes[idx - 1], self.classes[idx]
                self._sync_categories()
                self.show_model_screen()

        def move_down(_e):
            if idx < len(self.classes) - 1:
                self.classes[idx], self.classes[idx + 1] = self.classes[idx + 1], self.classes[idx]
                self._sync_categories()
                self.show_model_screen()

        def remove(_e):
            if len(self.classes) <= 1:
                self._alert_error("Classes", "Mantenha ao menos uma classe.")
                return
            self.classes.pop(idx)
            self._sync_categories()
            self.show_model_screen()

        arrows: list[ft.Control] = []
        if len(self.classes) > 1:
            arrows = [
                ft.IconButton(icon=ft.Icons.ARROW_UPWARD, icon_size=13, on_click=move_up,
                              disabled=(idx == 0), tooltip="Mover para cima", style=ft.ButtonStyle(padding=2)),
                ft.IconButton(icon=ft.Icons.ARROW_DOWNWARD, icon_size=13, on_click=move_down,
                              disabled=(idx == len(self.classes) - 1), tooltip="Mover para baixo", style=ft.ButtonStyle(padding=2)),
            ]

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(width=4, height=30, bgcolor=color, border_radius=ft.border_radius.only(top_left=4, bottom_left=4)),
                    ft.Text(str(idx + 1), size=FONT["caption"], color=COLORS["muted"], width=20),
                    ft.Text(name, size=FONT["label"], weight=ft.FontWeight.W_500, color=COLORS["text"], expand=True),
                    *arrows,
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=13, icon_color=COLORS["danger"],
                                  on_click=remove, tooltip="Remover", style=ft.ButtonStyle(padding=2)),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=SIZES["radius_sm"],
            height=36,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

    def _on_model_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            existing = set(self.weights_paths)
            for f in e.files:
                if f.path not in existing:
                    self.weights_paths.append(f.path)
                    existing.add(f.path)
            self.model_status = f"{len(self.weights_paths)} modelo(s) adicionado(s). Valide antes de iniciar."
            self.show_model_screen()

    def _validate_models(self) -> bool:
        from ultralytics import YOLO  # pylint: disable=import-outside-toplevel
        if not self.weights_paths:
            self._alert_error("Modelos inválidos", "Adicione ao menos um arquivo de pesos.")
            return False
        merged: list[str] = []
        failed: list[str] = []
        loaded: list[str] = []
        for raw in self.weights_paths:
            wp = Path(raw).expanduser()
            if not wp.exists():
                failed.append(f"{wp.name}: não encontrado")
                continue
            try:
                model = YOLO(str(wp))
            except Exception as exc:
                failed.append(f"{wp.name}: {exc}")
                continue
            names = getattr(model, "names", None)
            cls_list = self._extract_class_names(names)
            loaded.append(wp.name)
            for c in cls_list:
                if c not in merged:
                    merged.append(c)
        if failed:
            self._alert_error("Modelos inválidos", "Falha:\n" + "\n".join(f"• {f}" for f in failed))
            return False
        if not self._state_classes_authoritative() and merged:
            self.classes = merged
            self._sync_categories()
        preview = ", ".join(merged[:6]) + ("…" if len(merged) > 6 else "")
        self.model_status = f"{len(loaded)} modelo(s) validado(s): {', '.join(loaded)} | classes: {preview}"
        self.show_model_screen()
        return True

    @staticmethod
    def _extract_class_names(names) -> list[str]:
        if isinstance(names, dict):
            ordered = [names[k] for k in sorted(names)]
        elif isinstance(names, (list, tuple)):
            ordered = list(names)
        else:
            return []
        return list(normalize_class_names(str(n) for n in ordered))

    # ── Finalizar ──────────────────────────────────────────────────────────────

    def _finish(self):
        raw = self.data_root_str.strip()
        if not raw:
            self._alert_error("Dataset inválido", "Selecione uma fonte de dados.")
            return
        if not self.classes:
            self._alert_error("Classes inválidas", "Adicione ao menos uma classe.")
            return

        mode = self.mode
        state_mode = self.output_state_mode
        is_classification = mode is AnnotationTaskMode.CLASSIFICATION

        if state_mode == "manual":
            label = CLASSIFICATION_STATE_FILE_NAME if is_classification else "annotations.coco.json"
            if not self.selected_state_path or not self.selected_state_path.exists():
                self._alert_error("Estado inválido", f"Selecione um {label} antes de iniciar.")
                return
            self._ask_resume_and_finish(lambda resume: self._finish_with_resume(resume))
            return

        self._finish_with_resume(None)

    def _finish_with_resume(self, resume_answer: Optional[bool]):
        raw = self.data_root_str.strip()
        mode = self.mode
        state_mode = self.output_state_mode
        is_classification = mode is AnnotationTaskMode.CLASSIFICATION

        data_root = Path(raw).expanduser()
        weights_paths = (
            tuple(Path(p).expanduser() for p in self.weights_paths)
            if not is_classification else ()
        )
        if not is_classification and self.weights_paths:
            if not self._validate_models():
                return

        output_dir: Optional[Path] = None
        annotations_path: Optional[Path] = None
        resume_existing = False
        self._sync_categories()
        category_metadata = self.loaded_state_categories

        try:
            if is_classification:
                if state_mode == "resume_latest":
                    latest = latest_classification_state_for_sources(self._current_project_sources())
                    if not latest:
                        self._alert_error("Estado inválido", "Nenhum estado anterior encontrado.")
                        return
                    output_dir = latest.path
                    annotations_path = latest.state_path
                    resume_existing = True
                elif state_mode == "template_latest":
                    latest = latest_classification_state_for_sources(self._current_project_sources())
                    if not latest:
                        self._alert_error("Estado inválido", "Nenhum estado anterior encontrado.")
                        return
                    output_dir = create_new_output_dir(task_mode=mode, create_images_dir=False)
                elif state_mode == "manual":
                    resume_existing = bool(resume_answer)
                    output_dir = (
                        self.selected_state_path.parent if resume_existing
                        else create_new_output_dir(task_mode=mode, create_images_dir=False)
                    )
                    annotations_path = self.selected_state_path if resume_existing else None
                else:
                    output_dir = create_new_output_dir(task_mode=mode, create_images_dir=False)
            else:
                if state_mode == "resume_latest":
                    latest = latest_output_state_for_sources(self._current_project_sources())
                    if not latest:
                        self._alert_error("Estado inválido", "Nenhum estado anterior encontrado.")
                        return
                    output_dir = latest.path
                    annotations_path = latest.annotations_path
                    resume_existing = True
                elif state_mode == "template_latest":
                    latest = latest_output_state_for_sources(self._current_project_sources())
                    if not latest:
                        self._alert_error("Estado inválido", "Nenhum estado anterior encontrado.")
                        return
                    output_dir = create_new_output_dir(task_mode=mode)
                elif state_mode == "manual":
                    resume_existing = bool(resume_answer)
                    output_dir = (
                        self.selected_state_path.parent if resume_existing
                        else create_new_output_dir(task_mode=mode)
                    )
                    annotations_path = self.selected_state_path if resume_existing else None
                else:
                    output_dir = create_new_output_dir(task_mode=mode)
                if mode is AnnotationTaskMode.OBB and annotations_path is None:
                    annotations_path = output_dir / "annotations_obb.coco.json"

            config = AnnotationSessionConfig(
                mode=mode,
                data_root=data_root,
                weights_paths=weights_paths,
                target_classes=tuple(self.classes),
                output_dir=output_dir,
                annotations_path=annotations_path,
                resume_existing_annotations=resume_existing,
                category_metadata=category_metadata,
                classification_move_files=False,
            )
        except ValueError as exc:
            self._alert_error("Configuração inválida", str(exc))
            return

        save_startup_cache(data_root=data_root, weights_paths=list(weights_paths), mode=mode)
        self.on_complete(config)

    # ── Diálogo de confirmação de resume ─────────────────────────────────────

    def _ask_resume_and_finish(self, on_answer: "Callable[[bool], None]"):
        """Mostra dialog Sim/Não para decidir se continua ou usa como template."""
        self._resume_alert = ft.AlertDialog(
            modal=True,
            title=ft.Text("Carregar estado", weight=ft.FontWeight.BOLD),
            content=ft.Text(
                "Deseja continuar salvando neste estado?\n\n"
                "Sim: continua o output e carrega anotações antigas.\n"
                "Não: usa apenas classes/config e cria um output novo."
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._close_resume_alert(None, on_answer)),
                ft.TextButton("Não", on_click=lambda _: self._close_resume_alert(False, on_answer)),
                ft.ElevatedButton("Sim", on_click=lambda _: self._close_resume_alert(True, on_answer)),
            ],
        )
        self.page.overlay.append(self._resume_alert)
        self._resume_alert.open = True
        self.page.update()

    def _close_resume_alert(self, answer, on_answer):
        self._resume_alert.open = False
        self.page.overlay.remove(self._resume_alert)
        self.page.update()
        if answer is not None:
            on_answer(answer)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _sync_categories(self):
        metadata_by_name: dict[str, dict] = {}
        for cat in self.loaded_state_categories:
            name = str(cat.get("name", "")).strip()
            if name and name not in metadata_by_name:
                metadata_by_name[name] = dict(cat)
        synced = []
        for idx, name in enumerate(normalize_class_names(self.classes)):
            cat = dict(metadata_by_name.get(name, {}))
            cat["id"] = idx + 1
            cat["name"] = name
            cat.setdefault("color", CLASS_COLORS[idx % len(CLASS_COLORS)])
            cat.setdefault("supercategory", "none")
            synced.append(cat)
        self.classes = [c["name"] for c in synced]
        self.loaded_state_categories = tuple(synced)

    def _state_classes_authoritative(self) -> bool:
        return self.output_state_mode != "new" and bool(self.loaded_state_categories)

    def _current_project_sources(self) -> tuple[Path, ...]:
        if self.summary and self.summary.sources:
            return tuple(Path(s).expanduser() for s in self.summary.sources)
        raw = self.data_root_str.strip()
        return (Path(raw).expanduser(),) if raw else ()

    def _alert_error(self, title: str, message: str):
        if self._alert is None:
            self._alert = ft.AlertDialog(modal=True)
            self.page.overlay.append(self._alert)

        self._alert.title = ft.Text(title, weight=ft.FontWeight.BOLD)
        self._alert.content = ft.Text(message)
        self._alert.actions = [ft.TextButton("OK", on_click=lambda _: self._close_alert())]
        self._alert.open = True
        self.page.update()

    def _close_alert(self):
        if self._alert is None:
            return
        self._alert.open = False
        self.page.update()
