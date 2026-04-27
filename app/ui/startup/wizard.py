"""Responsive startup wizard used before the annotation screen."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, List, Optional

from ultralytics import YOLO

from app.config import DATA_ROOT, TARGET_CLASSES, WEIGHTS_PATH
from app.core.session import AnnotationSessionConfig, AnnotationTaskMode, normalize_class_names
from app.core.startup_cache import load_startup_cache, save_startup_cache
from app.sources.discovery import SourceDiscoveryService, SourceSummary
from app.ui.layout.responsive_window import apply_responsive_geometry
from app.ui.layout.scrollable_frame import ScrollableFrame
from app.ui.theme import COLORS, FONTS, SIZES, SPACING, build_scaled_theme

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
        self.ui = build_scaled_theme(self.root)
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
        self.weights_var = tk.StringVar(value=self._initial_path_text(self.cache.weights_path, WEIGHTS_PATH))
        self.model_status_var = tk.StringVar(value="Modelo ainda nao validado.")
        self.classes: List[str] = list(normalize_class_names(TARGET_CLASSES))
        self.summary: Optional[SourceSummary] = None

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
        steps = ["Modo", "Dataset", "Modelo"]
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
        self.show_model_screen()

    def show_model_screen(self):
        body = self._screen(
            "Escolha o modelo auxiliar",
            "Selecione os pesos YOLO e ajuste as classes iniciais para a sessao. Voce ainda podera editar classes durante a anotacao.",
            step=3,
        )
        form = self._build_card(body)
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)

        tk.Label(
            form,
            text="Arquivo de pesos (.pt)",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=self.fonts["label"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, self.spacing["sm"]))
        self._entry(form, self.weights_var).grid(row=1, column=0, columnspan=3, sticky="ew")

        actions = tk.Frame(form, bg=self.colors["panel"])
        actions.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(self.spacing["sm"], 0))
        actions.columnconfigure(0, weight=1)
        self._button(actions, "Selecionar modelo", self.browse_model).grid(
            row=0, column=1, padx=(0, self.spacing["sm"])
        )
        self._button(actions, "Validar modelo", self.validate_model).grid(row=0, column=2)

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
        self._footer(body, self.show_dataset_screen, self.finish, "Iniciar anotacao")

    def browse_model(self):
        initial = Path(self.weights_var.get()).expanduser() if self.weights_var.get().strip() else Path.home()
        path = filedialog.askopenfilename(
            title="Selecione o arquivo de pesos (.pt)",
            initialdir=str(initial.parent if initial.parent.exists() else Path.home()),
            filetypes=[("Pesos YOLO", "*.pt"), ("Todos os arquivos", "*.*")],
            parent=self.root,
        )
        if path:
            self.weights_var.set(path)
            self.model_status_var.set("Modelo alterado. Valide antes de iniciar para importar as classes.")

    def validate_model(self, *, import_classes: bool = True, refresh_screen: bool = True) -> bool:
        raw_path = self.weights_var.get().strip()
        if not raw_path:
            messagebox.showerror("Modelo invalido", "Selecione um arquivo de pesos antes de continuar.")
            return False
        weights_path = Path(raw_path).expanduser()
        if not weights_path.exists():
            messagebox.showerror("Modelo invalido", f"Pesos nao encontrados:\n{weights_path}")
            return False
        try:
            model = YOLO(str(weights_path))
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Modelo invalido", f"Nao foi possivel carregar o modelo:\n{weights_path}\n\n{exc}")
            self.model_status_var.set(f"Falha ao carregar: {weights_path.name}")
            return False

        names = getattr(model, "names", None)
        model_classes = self._model_class_names(names)
        if model_classes and import_classes:
            self.classes = model_classes
            self.model_status_var.set(
                f"Modelo carregado: {weights_path.name} | classes importadas: {', '.join(model_classes[:8])}"
                + ("..." if len(model_classes) > 8 else "")
            )
            if refresh_screen:
                self.show_model_screen()
            return True

        if model_classes:
            self.model_status_var.set(f"Modelo carregado: {weights_path.name} | {len(model_classes)} classes disponiveis.")
        else:
            self.model_status_var.set(f"Modelo carregado: {weights_path.name} | nenhuma classe encontrada em model.names")
        return True

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
        self._redraw_classes(panel)

    def _move_class(self, panel: tk.Frame, index: int, direction: int):
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.classes):
            return
        self.classes[index], self.classes[new_index] = self.classes[new_index], self.classes[index]
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
        self._redraw_classes(panel)

    def finish(self):
        raw_weights = self.weights_var.get().strip()
        raw_data_root = self.data_root_var.get().strip()
        if not raw_data_root:
            messagebox.showerror("Dataset invalido", "Selecione uma fonte de dados antes de iniciar.")
            return
        if not raw_weights:
            messagebox.showerror("Modelo invalido", "Selecione um arquivo de pesos antes de iniciar.")
            return
        weights_path = Path(raw_weights).expanduser()
        data_root = Path(raw_data_root).expanduser()
        if not self.validate_model(import_classes=False, refresh_screen=False):
            return
        try:
            mode = AnnotationTaskMode(self.mode_var.get())
            self.result = AnnotationSessionConfig(
                mode=mode,
                data_root=data_root,
                weights_path=weights_path,
                target_classes=tuple(self.classes),
            )
        except ValueError as exc:
            messagebox.showerror("Configuracao invalida", str(exc))
            return
        save_startup_cache(data_root=data_root, weights_path=weights_path, mode=mode)
        self.root.destroy()
