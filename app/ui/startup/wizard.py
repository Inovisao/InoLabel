"""Responsive startup wizard used before the annotation screen."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, List, Optional

from ultralytics import YOLO

from app.config import DATA_ROOT, WEIGHTS_PATH
from app.core.output_state import (
    OutputState,
    create_new_output_dir,
    latest_output_state_for_sources,
    list_output_states_for_sources,
    load_annotation_state,
)
from app.core.session import AnnotationSessionConfig, AnnotationTaskMode, normalize_class_names
from app.core.startup_cache import load_startup_cache, save_startup_cache
from app.sources.discovery import SourceDiscoveryService, SourceSummary
from app.ui.layout.responsive_window import apply_responsive_geometry
from app.ui.layout.scrollable_frame import ScrollableFrame
from app.ui.theme import COLORS, FONTS, SIZES, SPACING, install_scaled_theme

_THEME = COLORS
_PALETTE = [
    "#22c55e", "#3b82f6", "#f97316", "#e11d48",
    "#8b5cf6", "#14b8a6", "#eab308", "#ec4899",
    "#06b6d4", "#84cc16", "#f43f5e", "#6366f1",
]


def ask_startup_config() -> AnnotationSessionConfig:
    wizard = StartupWizard()
    result = wizard.run()
    if result is None:
        sys.exit(0)
    return result


class StartupWizard:
    """Three-step startup flow: mode, dataset, model/classes."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Configuracao inicial")
        self.ui = install_scaled_theme(self.root)
        self.colors = self.ui["colors"]
        self.fonts = self.ui["fonts"]
        self.spacing = self.ui["spacing"]
        self.sizes = self.ui["sizes"]

        self.root.configure(bg=self.colors["bg"])
        apply_responsive_geometry(self.root, width_ratio=0.92, height_ratio=0.88)
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)

        self.cache = load_startup_cache()
        self.discovery = SourceDiscoveryService()
        self.result: Optional[AnnotationSessionConfig] = None
        cached_mode = self.cache.mode or AnnotationTaskMode.TRACKING
        self.mode_var = tk.StringVar(value=cached_mode.value)
        self.data_root_var = tk.StringVar(value=self._initial_path_text(self.cache.data_root, DATA_ROOT))
        # Lista de caminhos de modelos (ensemble)
        if self.cache.weights_paths:
            self.weights_paths: List[str] = [str(p) for p in self.cache.weights_paths]
        elif Path(WEIGHTS_PATH).exists():
            self.weights_paths = [str(WEIGHTS_PATH)]
        else:
            self.weights_paths = []
        self.model_status_var = tk.StringVar(value="Modelos ainda nao validados.")
        self.output_state_mode_var = tk.StringVar(value="new")
        self.output_state_status_var = tk.StringVar(value="")
        self.selected_state_path: Optional[Path] = None
        self.loaded_state_categories: tuple[dict, ...] = ()
        self.classes: List[str] = []
        self.class_panel: Optional[tk.Frame] = None
        self.summary: Optional[SourceSummary] = None
        self.output_states: list[OutputState] = []

        self.page = tk.Frame(self.root, bg=self.colors["bg"])
        self.page.pack(fill=tk.BOTH, expand=True)
        self.root.bind("<Configure>", self._on_resize)
        self.show_mode_screen()

    @staticmethod
    def _initial_path_text(cached_path: Optional[Path], fallback_path: Path) -> str:
        if cached_path is not None:
            return str(cached_path)
        fallback = Path(fallback_path)
        if fallback.exists():
            return str(fallback)
        return ""

    def run(self) -> Optional[AnnotationSessionConfig]:
        self.root.mainloop()
        return self.result

    def cancel(self):
        self.result = None
        self.root.destroy()

    def _clear(self):
        for child in self.page.winfo_children():
            child.destroy()

    def _on_resize(self, _event):
        wrap = max(420, min(self.sizes["content_max_w"], self.root.winfo_width() - (self.spacing["xl"] * 2)))
        for widget in self.root.winfo_children():
            self._update_wraplengths(widget, wrap)

    def _update_wraplengths(self, widget, wrap: int):
        if isinstance(widget, tk.Label) and getattr(widget, "_responsive_wrap", False):
            widget.configure(wraplength=wrap)
        for child in widget.winfo_children():
            self._update_wraplengths(child, wrap)

    def _step_indicator(self, parent, current: int):
        steps = ["Modo", "Dataset", "Modelo", "Estado"]
        row = tk.Frame(parent, bg=self.colors["bg"])
        row.pack(fill=tk.X, pady=(0, self.spacing["lg"]))

        for i, label in enumerate(steps, 1):
            is_done = i < current
            is_active = i == current

            if is_done:
                c_bg, c_fg = self.colors["primary"], self.colors["fg_light"]
                l_fg = self.colors["text"]
            elif is_active:
                c_bg, c_fg = self.colors["accent"], self.colors["text"]
                l_fg = self.colors["text"]
            else:
                c_bg, c_fg = self.colors["neutral"], self.colors["muted"]
                l_fg = self.colors["muted"]

            number = tk.Label(
                row, text="✓" if is_done else str(i),
                font=self.fonts["tag"],
                bg=c_bg, fg=c_fg,
                padx=self.spacing["sm"], pady=max(3, self.spacing["xs"]),
                cursor="hand2",
            )
            number.pack(side=tk.LEFT)

            name = tk.Label(
                row, text=label,
                font=self.fonts["tag"],
                bg=self.colors["bg"], fg=l_fg,
                cursor="hand2",
            )
            name.pack(side=tk.LEFT, padx=(self.spacing["xs"], 0))
            number.bind("<Button-1>", lambda _event, step=i: self._go_to_step(step))
            name.bind("<Button-1>", lambda _event, step=i: self._go_to_step(step))

            if i < len(steps):
                tk.Frame(
                    row, height=2, width=36,
                    bg=self.colors["primary"] if is_done else self.colors["border"],
                ).pack(side=tk.LEFT, padx=self.spacing["sm"])

    def _go_to_step(self, step: int):
        if step == 1:
            self.show_mode_screen()
            return
        if step == 2:
            self.show_dataset_screen()
            return
        if step == 3:
            if self.summary is None:
                self.validate_dataset_and_continue()
            else:
                self.show_state_screen()
            return
        if step == 4:
            if self.summary is None:
                self.validate_dataset_and_continue()
            else:
                self.show_model_screen()

    def _screen(self, title: str, subtitle: str, *, step: int):
        self._clear()

        # Step indicator — fixed above the scroll
        step_bar = tk.Frame(self.page, bg=self.colors["bg"])
        step_bar.pack(fill=tk.X, padx=self.spacing["xl"], pady=(self.spacing["lg"], 0))
        self._step_indicator(step_bar, step)

        scroll = ScrollableFrame(self.page, bg=self.colors["bg"])
        scroll.pack(fill=tk.BOTH, expand=True)
        outer = scroll.content
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=0)
        outer.columnconfigure(2, weight=1)

        width = min(self.sizes["content_max_w"], max(self.sizes["content_min_w"], self.root.winfo_width() - self.spacing["2xl"]))
        body = tk.Frame(outer, bg=self.colors["bg"], padx=self.spacing["xl"], pady=self.spacing["xl"], width=width)
        body.grid(row=0, column=1, sticky="n")
        body.columnconfigure(0, weight=1)

        title_label = tk.Label(
            body,
            text=title,
            font=self.fonts["title"],
            bg=self.colors["bg"],
            fg=self.colors["text"],
            anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="ew", pady=(0, self.spacing["sm"]))

        subtitle_label = tk.Label(
            body,
            text=subtitle,
            font=self.fonts["body"],
            bg=self.colors["bg"],
            fg=self.colors["muted"],
            justify=tk.LEFT,
            anchor="w",
        )
        subtitle_label._responsive_wrap = True
        subtitle_label.grid(row=1, column=0, sticky="ew", pady=(0, self.spacing["xl"]))
        return body

    def _button(self, parent, text: str, command: Callable, *, primary: bool = False):
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
        if primary:
            button.configure(
                bg=self.colors["primary"],
                fg=self.colors["fg_light"],
                activebackground=self.colors["primary_active"],
                activeforeground=self.colors["fg_light"],
            )
        else:
            button.configure(
                bg=self.colors["neutral"],
                fg=self.colors["text"],
                activebackground=self.colors["neutral_active"],
                activeforeground=self.colors["text"],
            )
        return button

    def _footer(self, parent, back: Optional[Callable], next_: Callable, next_text: str = "Continuar"):
        footer = tk.Frame(parent, bg=self.colors["bg"])
        footer.grid(row=99, column=0, sticky="ew", pady=(self.spacing["xl"], 0))
        footer.columnconfigure(0, weight=1)
        if back is not None:
            self._button(footer, "Voltar", back).grid(row=0, column=1, padx=(0, self.spacing["sm"]), sticky="ew")
        self._button(footer, next_text, next_, primary=True).grid(row=0, column=2, sticky="ew")

    def _build_card(self, parent):
        card = tk.Frame(
            parent,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0,
            padx=self.spacing["lg"],
            pady=self.spacing["lg"],
        )
        return card

    def show_mode_screen(self):
        body = self._screen(
            "Escolha o fluxo de anotacao",
            "Defina se esta sessao vai manter identidade dos objetos ao longo dos frames ou gerar anotacoes de deteccao padrao.",
            step=1,
        )
        body.rowconfigure(2, weight=1)
        options = tk.Frame(body, bg=self.colors["bg"])
        options.grid(row=2, column=0, sticky="nsew")
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)

        self._mode_card(options, AnnotationTaskMode.TRACKING, "Mantem IDs por objeto e usa rastreamento multiclass.").grid(
            row=0, column=0, sticky="nsew", padx=(0, 10), pady=8
        )
        self._mode_card(options, AnnotationTaskMode.DETECTION, "Gera caixas independentes, sem IDs de tracking.").grid(
            row=0, column=1, sticky="nsew", padx=(10, 0), pady=8
        )
        self._footer(body, None, self.show_dataset_screen)

    def _mode_card(self, parent, mode: AnnotationTaskMode, description: str):
        card = self._build_card(parent)
        card.columnconfigure(0, weight=1)
        radio = tk.Radiobutton(
            card,
            text=mode.label,
            value=mode.value,
            variable=self.mode_var,
            font=self.fonts["heading"],
            bg=self.colors["panel"],
            fg=self.colors["text"],
            activebackground=self.colors["panel"],
            selectcolor=self.colors["panel_alt"],
            anchor="w",
            command=lambda: self.mode_var.set(mode.value),
        )
        radio.grid(row=0, column=0, sticky="ew")
        desc = tk.Label(
            card,
            text=description,
            font=self.fonts["caption"],
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            justify=tk.LEFT,
            anchor="w",
        )
        desc._responsive_wrap = True
        desc.grid(row=1, column=0, sticky="ew", pady=(self.spacing["sm"], 0))
        return card

    def show_dataset_screen(self):
        body = self._screen(
            "Importe o dataset que sera anotado",
            "Selecione uma pasta, video, imagem unica ou lista de imagens. A validacao ocorre antes de abrir a tela de anotacao.",
            step=2,
        )
        body.columnconfigure(0, weight=1)
        form = self._build_card(body)
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)

        tk.Label(
            form,
            text="Fonte de dados",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=self.fonts["label"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, self.spacing["sm"]))
        entry = self._entry(form, self.data_root_var)
        entry.grid(row=1, column=0, columnspan=3, sticky="ew")

        actions = tk.Frame(form, bg=self.colors["panel"])
        actions.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(self.spacing["sm"], 0))
        actions.columnconfigure(0, weight=1)
        self._button(actions, "Selecionar pasta", self.browse_dataset_folder).grid(
            row=0, column=1, padx=(0, self.spacing["sm"])
        )
        self._button(actions, "Selecionar arquivo", self.browse_dataset_file).grid(row=0, column=2)

        summary_text = self._build_summary_text()
        summary = tk.Label(
            form,
            text=summary_text,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=self.fonts["caption"],
            justify=tk.LEFT,
            anchor="w",
        )
        summary._responsive_wrap = True
        summary.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(self.spacing["md"], 0))
        self._footer(body, self.show_mode_screen, self.validate_dataset_and_continue)

    def _entry(self, parent, variable: tk.StringVar):
        return tk.Entry(
            parent,
            textvariable=variable,
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

    def browse_dataset_folder(self):
        initial = Path(self.data_root_var.get()).expanduser() if self.data_root_var.get().strip() else Path.home()
        path = filedialog.askdirectory(
            title="Selecione a pasta com imagens ou videos",
            initialdir=str(initial if initial.exists() else Path.home()),
            parent=self.root,
        )
        if path:
            self.data_root_var.set(path)
            self.summary = None
            self.show_dataset_screen()

    def browse_dataset_file(self):
        initial = Path(self.data_root_var.get()).expanduser() if self.data_root_var.get().strip() else Path.home()
        path = filedialog.askopenfilename(
            title="Selecione uma imagem, video ou lista",
            initialdir=str(initial.parent if initial.parent.exists() else Path.home()),
            filetypes=[
                ("Fontes suportadas", "*.mp4 *.avi *.mov *.mkv *.jpg *.jpeg *.png *.bmp *.tif *.tiff *.txt *.lst"),
                ("Todos os arquivos", "*.*"),
            ],
            parent=self.root,
        )
        if path:
            self.data_root_var.set(path)
            self.summary = None
            self.show_dataset_screen()

    def _build_summary_text(self) -> str:
        if self.summary is None:
            return "Nenhuma fonte validada ainda."
        return (
            f"Fontes encontradas: {self.summary.total} | "
            f"videos: {self.summary.video_count} | "
            f"imagens: {self.summary.image_count} | "
            f"listas: {self.summary.image_list_count}"
        )

    def validate_dataset_and_continue(self):
        raw_path = self.data_root_var.get().strip()
        if not raw_path:
            messagebox.showerror("Dataset invalido", "Selecione uma fonte de dados antes de continuar.")
            return
        data_root = Path(raw_path).expanduser()
        if not data_root.exists():
            messagebox.showerror("Dataset invalido", f"Fonte nao encontrada:\n{data_root}")
            return
        self.summary = self.discovery.summarize(data_root)
        if not self.summary.has_sources:
            messagebox.showerror("Dataset invalido", f"Nenhuma fonte valida encontrada em:\n{data_root}")
            return
        self.show_state_screen()

    def show_model_screen(self):
        body = self._screen(
            "Escolha os modelos auxiliares",
            "Adicione um ou mais pesos YOLO. Com varios modelos as deteccoes sao mescladas via NMS (ensemble). Ajuste as classes iniciais para a sessao.",
            step=4,
        )
        form = self._build_card(body)
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)

        tk.Label(
            form,
            text="Modelos (.pt)",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=self.fonts["label"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, self.spacing["sm"]))

        # Lista de modelos
        models_panel = tk.Frame(form, bg=self.colors["panel"])
        models_panel.grid(row=1, column=0, columnspan=3, sticky="ew")
        models_panel.columnconfigure(0, weight=1)
        self._redraw_models(models_panel)

        actions = tk.Frame(form, bg=self.colors["panel"])
        actions.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(self.spacing["sm"], 0))
        actions.columnconfigure(0, weight=1)
        self._button(actions, "Adicionar modelo(s)", self.browse_model).grid(
            row=0, column=1, padx=(0, self.spacing["sm"])
        )
        self._button(actions, "Validar modelos", self.validate_models_for_current_state).grid(row=0, column=2)

        tk.Label(
            form,
            text="Classes",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=self.fonts["label"],
            anchor="w",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(self.spacing["lg"], self.spacing["sm"]))
        class_panel = tk.Frame(form, bg=self.colors["panel"])
        class_panel.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.class_panel = class_panel
        self._redraw_classes(class_panel)

        model_status = tk.Label(
            form,
            textvariable=self.model_status_var,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=self.fonts["caption"],
            justify=tk.LEFT,
            anchor="w",
        )
        model_status._responsive_wrap = True
        model_status.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(self.spacing["lg"], 0))

        summary = tk.Label(
            form,
            text=f"Modo escolhido: {AnnotationTaskMode(self.mode_var.get()).label}. Dataset validado: {self._build_summary_text()}",
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=self.fonts["caption"],
            justify=tk.LEFT,
            anchor="w",
        )
        summary._responsive_wrap = True
        summary.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(self.spacing["md"], 0))
        self._footer(body, self.show_state_screen, self.finish, "Iniciar anotacao")

    def _redraw_models(self, panel: tk.Frame):
        for child in panel.winfo_children():
            child.destroy()
        panel.columnconfigure(0, weight=1)

        if not self.weights_paths:
            tk.Label(
                panel,
                text="Nenhum modelo adicionado.",
                bg=self.colors["panel"],
                fg=self.colors["muted"],
                font=self.fonts["caption"],
                anchor="w",
            ).grid(row=0, column=0, sticky="ew")
            return

        for idx, path_str in enumerate(self.weights_paths):
            row_frame = tk.Frame(
                panel,
                bg=self.colors["input_bg"],
                highlightbackground=self.colors["border"],
                highlightthickness=1,
                bd=0,
            )
            row_frame.grid(row=idx, column=0, sticky="ew", pady=(0, self.spacing["xs"]))
            row_frame.columnconfigure(0, weight=1)

            name = Path(path_str).name
            tk.Label(
                row_frame,
                text=name,
                bg=self.colors["input_bg"],
                fg=self.colors["text"],
                font=self.fonts["body"],
                anchor="w",
                padx=self.spacing["sm"],
                pady=self.spacing["xs"],
            ).grid(row=0, column=0, sticky="ew")

            def _remove(i=idx):
                self.weights_paths.pop(i)
                self.show_model_screen()

            tk.Button(
                row_frame,
                text="×",
                bg=self.colors["input_bg"],
                fg=self.colors["danger"],
                font=self.fonts["button"],
                relief=tk.FLAT,
                cursor="hand2",
                command=_remove,
            ).grid(row=0, column=1, padx=(0, self.spacing["xs"]))

    def show_state_screen(self):
        project_sources = self._current_project_sources()
        self.output_states = list_output_states_for_sources(project_sources) if project_sources else []
        latest = self.output_states[-1] if self.output_states else None
        if latest is not None and self.output_state_mode_var.get() == "new" and self.selected_state_path is None:
            self.output_state_mode_var.set("resume_latest")
            self.selected_state_path = latest.annotations_path
            self.output_state_status_var.set(f"Ultimo estado encontrado: {latest.label}")
            self._apply_state_template(latest.annotations_path)
        elif latest is None and self.output_state_mode_var.get() in {"resume_latest", "template_latest"}:
            self.output_state_mode_var.set("new")
            self.selected_state_path = None
            self.loaded_state_categories = ()
            self.classes = []
            self.output_state_status_var.set("Nenhum estado salvo encontrado para este projeto.")

        body = self._screen(
            "Escolha o estado de saida",
            "Continue um output deste projeto, use um annotations.coco.json manualmente, ou crie um output novo isolado.",
            step=3,
        )
        form = self._build_card(body)
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)

        latest_text = latest.label if latest else "Nenhum estado anterior encontrado."
        self._state_option(
            form,
            row=0,
            value="resume_latest",
            title="Continuar ultimo estado",
            description=latest_text,
            enabled=latest is not None,
        )
        self._state_option(
            form,
            row=1,
            value="template_latest",
            title="Usar ultimo estado como modelo",
            description="Carrega classes/configuracoes do ultimo output deste projeto e cria um output novo vazio.",
            enabled=latest is not None,
        )
        self._state_option(
            form,
            row=2,
            value="manual",
            title="Escolher annotations.coco.json manualmente",
            description="Permite continuar ou usar como modelo qualquer estado salvo.",
            enabled=True,
        )
        self._state_option(
            form,
            row=3,
            value="new",
            title="Criar estado novo",
            description="Cria uma pasta outputs/output_dataset{indice}_{data_hora} sem misturar anotacoes antigas.",
            enabled=True,
        )

        manual_row = tk.Frame(form, bg=self.colors["panel"])
        manual_row.grid(row=4, column=0, sticky="ew", pady=(self.spacing["md"], 0))
        manual_row.columnconfigure(0, weight=1)
        tk.Label(
            manual_row,
            textvariable=self.output_state_status_var,
            font=self.fonts["caption"],
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            anchor="w",
            justify=tk.LEFT,
        ).grid(row=0, column=0, sticky="ew", padx=(0, self.spacing["sm"]))
        self._button(manual_row, "Selecionar arquivo", self.browse_annotation_state).grid(row=0, column=1)

        self._footer(body, self.show_dataset_screen, self.show_model_screen)

    def _state_option(self, parent, *, row: int, value: str, title: str, description: str, enabled: bool):
        option = tk.Frame(parent, bg=self.colors["panel"])
        option.grid(row=row, column=0, sticky="ew", pady=(0, self.spacing["sm"]))
        option.columnconfigure(0, weight=1)
        state = tk.NORMAL if enabled else tk.DISABLED
        radio = tk.Radiobutton(
            option,
            text=title,
            value=value,
            variable=self.output_state_mode_var,
            font=self.fonts["label"],
            bg=self.colors["panel"],
            fg=self.colors["text"],
            activebackground=self.colors["panel"],
            selectcolor=self.colors["panel_alt"],
            anchor="w",
            state=state,
            command=lambda v=value: self._on_state_mode_changed(v),
        )
        radio.grid(row=0, column=0, sticky="ew")
        tk.Label(
            option,
            text=description,
            font=self.fonts["caption"],
            bg=self.colors["panel"],
            fg=self.colors["muted"] if enabled else self.colors["disabled_fg"],
            anchor="w",
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="ew", padx=(self.spacing["lg"], 0))

    def _on_state_mode_changed(self, value: str):
        if value in {"resume_latest", "template_latest"}:
            latest = latest_output_state_for_sources(self._current_project_sources())
            self.selected_state_path = latest.annotations_path if latest is not None else None
            if latest is not None:
                self.output_state_status_var.set(f"Estado selecionado: {latest.label}")
                self._apply_state_template(latest.annotations_path)
            else:
                self.output_state_mode_var.set("new")
                self.loaded_state_categories = ()
                self.classes = []
                self.output_state_status_var.set("Nenhum estado salvo encontrado para este projeto.")
                self._refresh_classes_panel()
        elif value == "new":
            self.selected_state_path = None
            self.loaded_state_categories = ()
            self.classes = []
            self.output_state_status_var.set("Novo estado sera criado ao iniciar.")
            self._refresh_classes_panel()

    def browse_annotation_state(self):
        initial = self.selected_state_path.parent if self.selected_state_path else Path.cwd()
        path = filedialog.askopenfilename(
            title="Selecione annotations.coco.json",
            initialdir=str(initial if initial.exists() else Path.cwd()),
            filetypes=[
                ("COCO annotations", "annotations.coco.json __annotations.coco.json *.json"),
                ("Todos os arquivos", "*.*"),
            ],
            parent=self.root,
        )
        if not path:
            return
        try:
            state = load_annotation_state(Path(path))
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Estado invalido", str(exc))
            return
        if not state.class_names:
            messagebox.showerror("Estado invalido", "O arquivo nao possui categorias/classes para carregar.")
            return
        self.selected_state_path = state.annotations_path
        self.output_state_mode_var.set("manual")
        self.output_state_status_var.set(
            f"Selecionado: {state.annotations_path} | {len(state.class_names)} classes | "
            f"{state.image_count} imagens | {state.annotation_count} anotacoes"
        )
        self.classes = list(state.class_names)
        self.loaded_state_categories = state.categories
        self._sync_loaded_categories_to_classes()
        self._refresh_classes_panel()

    def _apply_state_template(self, annotations_path: Path) -> bool:
        try:
            state = load_annotation_state(annotations_path)
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Estado invalido", str(exc))
            return False
        if not state.class_names:
            messagebox.showerror("Estado invalido", "O estado selecionado nao possui classes.")
            return False
        self.classes = list(state.class_names)
        self.loaded_state_categories = state.categories
        self._sync_loaded_categories_to_classes()
        if state.task_mode is not None:
            self.mode_var.set(state.task_mode.value)
        self._refresh_classes_panel()
        return True

    def _sync_loaded_categories_to_classes(self):
        metadata_by_name = {}
        for cat in self.loaded_state_categories:
            name = str(cat.get("name", "")).strip()
            if name and name not in metadata_by_name:
                metadata_by_name[name] = dict(cat)

        synced = []
        for idx, name in enumerate(normalize_class_names(self.classes)):
            cat = dict(metadata_by_name.get(name, {}))
            cat["id"] = idx + 1
            cat["name"] = name
            cat.setdefault("color", _PALETTE[idx % len(_PALETTE)])
            cat.setdefault("supercategory", "none")
            synced.append(cat)

        self.classes = [cat["name"] for cat in synced]
        self.loaded_state_categories = tuple(synced)

    def _refresh_classes_panel(self):
        panel = getattr(self, "class_panel", None)
        if panel is None:
            return
        try:
            exists = panel.winfo_exists()
        except tk.TclError:
            exists = False
        if exists:
            self._redraw_classes(panel)

    def _state_classes_are_authoritative(self) -> bool:
        return self.output_state_mode_var.get() != "new" and bool(self.loaded_state_categories)

    def _current_project_sources(self) -> tuple[Path, ...]:
        if self.summary is not None and self.summary.sources:
            return tuple(Path(source).expanduser() for source in self.summary.sources)
        raw_path = self.data_root_var.get().strip()
        return (Path(raw_path).expanduser(),) if raw_path else ()

    def browse_model(self):
        initial_dir = Path.home()
        if self.weights_paths:
            candidate = Path(self.weights_paths[-1]).parent
            if candidate.exists():
                initial_dir = candidate
        paths = filedialog.askopenfilenames(
            title="Selecione um ou mais arquivos de pesos (.pt)",
            initialdir=str(initial_dir),
            filetypes=[("Pesos YOLO", "*.pt"), ("Todos os arquivos", "*.*")],
            parent=self.root,
        )
        if paths:
            existing = set(self.weights_paths)
            added = [p for p in paths if p not in existing]
            self.weights_paths.extend(added)
            self.model_status_var.set(
                f"{len(added)} modelo(s) adicionado(s). Valide antes de iniciar."
            )
            self.show_model_screen()

    def validate_models(self, *, import_classes: bool = True, refresh_screen: bool = True) -> bool:
        if not self.weights_paths:
            messagebox.showerror("Modelos invalidos", "Adicione ao menos um arquivo de pesos antes de continuar.")
            return False

        merged_classes: List[str] = []
        failed: List[str] = []
        loaded_names: List[str] = []

        for raw_path in self.weights_paths:
            weights_path = Path(raw_path).expanduser()
            if not weights_path.exists():
                failed.append(f"{weights_path.name}: arquivo nao encontrado")
                continue
            try:
                model = YOLO(str(weights_path))
            except Exception as exc:  # pylint: disable=broad-except
                failed.append(f"{weights_path.name}: {exc}")
                continue
            names = getattr(model, "names", None)
            model_classes = self._model_class_names(names)
            loaded_names.append(weights_path.name)
            for cls in model_classes:
                if cls not in merged_classes:
                    merged_classes.append(cls)

        if failed:
            messagebox.showerror(
                "Modelos invalidos",
                "Falha ao carregar:\n" + "\n".join(f"• {f}" for f in failed),
            )
            return False

        if merged_classes and import_classes:
            self.classes = merged_classes
            self._sync_loaded_categories_to_classes()

        count = len(loaded_names)
        cls_preview = ", ".join(merged_classes[:8]) + ("..." if len(merged_classes) > 8 else "")
        self.model_status_var.set(
            f"{count} modelo(s) validado(s): {', '.join(loaded_names)} | "
            f"classes: {cls_preview}"
        )
        if refresh_screen:
            self.show_model_screen()
        return True

    def validate_models_for_current_state(self) -> bool:
        import_classes = not self._state_classes_are_authoritative()
        ok = self.validate_models(import_classes=import_classes, refresh_screen=True)
        if ok and not import_classes:
            self.model_status_var.set(
                f"{self.model_status_var.get()} | classes preservadas do estado selecionado"
            )
        return ok

    def validate_model(self, *, import_classes: bool = True, refresh_screen: bool = True) -> bool:
        """Alias mantido para compatibilidade interna."""
        return self.validate_models(import_classes=import_classes, refresh_screen=refresh_screen)

    @staticmethod
    def _model_class_names(names) -> List[str]:
        if isinstance(names, dict):
            ordered = [names[key] for key in sorted(names.keys())]
        elif isinstance(names, list):
            ordered = names
        else:
            return []
        return list(normalize_class_names(str(name) for name in ordered))

    def _redraw_classes(self, panel: tk.Frame):
        self._class_editor_open = False
        for child in panel.winfo_children():
            child.destroy()
        panel.columnconfigure(0, weight=1)
        for idx, name in enumerate(self.classes):
            color = _PALETTE[idx % len(_PALETTE)]
            row = tk.Frame(
                panel,
                bg=self.colors["input_bg"],
                highlightbackground=color,
                highlightthickness=1,
                bd=0,
            )
            row.pack(fill=tk.X, pady=(0, self.spacing["sm"]))
            row.columnconfigure(1, weight=1)

            tk.Label(
                row,
                text="",
                bg=color,
                width=2,
            ).grid(row=0, column=0, sticky="nsw")
            tk.Label(
                row,
                text=f"{idx + 1} {name}",
                font=self.fonts["tag"],
                padx=self.spacing["sm"],
                pady=self.spacing["sm"],
                bg=self.colors["input_bg"],
                fg=self.colors["text"],
                anchor="w",
            ).grid(row=0, column=1, sticky="ew")
            if len(self.classes) > 1:
                tk.Button(
                    row,
                    text="↑",
                    font=self.fonts["tag"],
                    padx=self.spacing["sm"],
                    pady=self.spacing["sm"],
                    bd=0,
                    relief=tk.FLAT,
                    cursor="hand2" if idx > 0 else "arrow",
                    bg=self.colors["neutral"],
                    fg=self.colors["text"],
                    activebackground=self.colors["neutral_active"],
                    activeforeground=self.colors["text"],
                    disabledforeground=self.colors["muted"],
                    state=(tk.NORMAL if idx > 0 else tk.DISABLED),
                    command=lambda i=idx: self._move_class(panel, i, -1),
                ).grid(row=0, column=2, sticky="e", padx=(self.spacing["sm"], 0))
                tk.Button(
                    row,
                    text="↓",
                    font=self.fonts["tag"],
                    padx=self.spacing["sm"],
                    pady=self.spacing["sm"],
                    bd=0,
                    relief=tk.FLAT,
                    cursor="hand2" if idx < len(self.classes) - 1 else "arrow",
                    bg=self.colors["neutral"],
                    fg=self.colors["text"],
                    activebackground=self.colors["neutral_active"],
                    activeforeground=self.colors["text"],
                    disabledforeground=self.colors["muted"],
                    state=(tk.NORMAL if idx < len(self.classes) - 1 else tk.DISABLED),
                    command=lambda i=idx: self._move_class(panel, i, 1),
                ).grid(row=0, column=3, sticky="e", padx=(self.spacing["xs"], 0))
            remove_state = tk.NORMAL if len(self.classes) > 1 else tk.DISABLED
            remove_btn = tk.Button(
                row,
                text="Remover",
                font=self.fonts["tag"],
                padx=self.spacing["sm"],
                pady=self.spacing["sm"],
                bd=0,
                relief=tk.FLAT,
                cursor="hand2" if len(self.classes) > 1 else "arrow",
                bg=self.colors["danger"],
                fg=self.colors["fg_light"],
                activebackground=self.colors["danger"],
                activeforeground=self.colors["fg_light"],
                disabledforeground=self.colors["disabled_fg"],
                state=remove_state,
                command=lambda n=name: self._remove_class(panel, n),
            )
            remove_btn.grid(row=0, column=4, sticky="e", padx=(self.spacing["sm"], 0))
        self._button(panel, "+ Nova classe", lambda: self._show_class_entry(panel)).pack(
            fill=tk.X,
            pady=self.spacing["xs"],
        )

    def _remove_class(self, panel: tk.Frame, name: str):
        if len(self.classes) <= 1:
            messagebox.showwarning("Classes", "Mantenha ao menos uma classe para iniciar a anotacao.")
            return
        self.classes = [item for item in self.classes if item != name]
        self._sync_loaded_categories_to_classes()
        self._redraw_classes(panel)

    def _move_class(self, panel: tk.Frame, index: int, direction: int):
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.classes):
            return
        self.classes[index], self.classes[new_index] = self.classes[new_index], self.classes[index]
        self._sync_loaded_categories_to_classes()
        self._redraw_classes(panel)

    def _show_class_entry(self, panel: tk.Frame):
        if getattr(self, "_class_editor_open", False):
            return
        self._class_editor_open = True

        children = panel.winfo_children()
        if children:
            children[-1].destroy()
        var = tk.StringVar()
        editor = tk.Frame(panel, bg=self.colors["panel"])
        editor.pack(fill=tk.X, pady=self.spacing["xs"])
        editor.columnconfigure(0, weight=1)

        entry = self._entry(editor, var)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, self.spacing["sm"]))
        self._button(editor, "Adicionar", lambda: self._confirm_class(panel, var), primary=True).grid(
            row=0,
            column=1,
            padx=(0, self.spacing["sm"]),
        )
        self._button(editor, "Cancelar", lambda: self._redraw_classes(panel)).grid(row=0, column=2)
        entry.focus_set()
        entry.bind("<Return>", lambda _event: self._confirm_class(panel, var))
        entry.bind("<Escape>", lambda _event: self._redraw_classes(panel))

    def _confirm_class(self, panel: tk.Frame, var: tk.StringVar):
        name = var.get().strip()
        if not name:
            self._redraw_classes(panel)
            return
        if name not in self.classes:
            self.classes.append(name)
            self._sync_loaded_categories_to_classes()
        self._redraw_classes(panel)

    def finish(self):
        raw_data_root = self.data_root_var.get().strip()
        if not raw_data_root:
            messagebox.showerror("Dataset invalido", "Selecione uma fonte de dados antes de iniciar.")
            return
        if not self.weights_paths:
            messagebox.showerror("Modelo invalido", "Adicione ao menos um arquivo de pesos antes de iniciar.")
            return
        if not self.classes:
            messagebox.showerror("Classes invalidas", "Adicione ao menos uma classe antes de iniciar.")
            return
        data_root = Path(raw_data_root).expanduser()
        weights_paths = tuple(Path(p).expanduser() for p in self.weights_paths)
        if not self.validate_models(import_classes=False, refresh_screen=False):
            return
        state_mode = self.output_state_mode_var.get()
        output_dir = None
        annotations_path = None
        resume_existing = False
        category_metadata: tuple[dict, ...] = ()

        if state_mode == "resume_latest":
            latest = latest_output_state_for_sources(self._current_project_sources())
            if latest is None:
                messagebox.showerror("Estado invalido", "Nenhum estado anterior foi encontrado para este projeto.")
                return
            self.selected_state_path = latest.annotations_path
            output_dir = latest.path
            annotations_path = latest.annotations_path
            resume_existing = True
        elif state_mode == "template_latest":
            latest = latest_output_state_for_sources(self._current_project_sources())
            if latest is None:
                messagebox.showerror("Estado invalido", "Nenhum estado anterior foi encontrado para este projeto.")
                return
            self.selected_state_path = latest.annotations_path
            output_dir = create_new_output_dir()
        elif state_mode == "manual":
            if self.selected_state_path is None:
                messagebox.showerror("Estado invalido", "Selecione um annotations.coco.json antes de iniciar.")
                return
            if not self.selected_state_path.exists():
                messagebox.showerror("Estado invalido", f"Arquivo nao encontrado:\n{self.selected_state_path}")
                return
            answer = messagebox.askyesnocancel(
                "Carregar estado",
                "Deseja continuar salvando neste estado?\n\n"
                "Sim: continua o output selecionado e carrega anotacoes antigas.\n"
                "Nao: usa apenas classes/configuracoes e cria um output novo.",
                parent=self.root,
            )
            if answer is None:
                return
            resume_existing = bool(answer)
            output_dir = self.selected_state_path.parent if resume_existing else create_new_output_dir()
            annotations_path = self.selected_state_path if resume_existing else None
        else:
            output_dir = create_new_output_dir()

        self._sync_loaded_categories_to_classes()
        category_metadata = self.loaded_state_categories

        try:
            mode = AnnotationTaskMode(self.mode_var.get())
            self.result = AnnotationSessionConfig(
                mode=mode,
                data_root=data_root,
                weights_paths=weights_paths,
                target_classes=tuple(self.classes),
                output_dir=output_dir,
                annotations_path=annotations_path,
                resume_existing_annotations=resume_existing,
                category_metadata=category_metadata,
            )
        except ValueError as exc:
            messagebox.showerror("Configuracao invalida", str(exc))
            return
        save_startup_cache(data_root=data_root, weights_paths=weights_paths, mode=mode)
        self.root.destroy()
