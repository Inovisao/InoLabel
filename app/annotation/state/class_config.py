from app.annotation.shared import *
from app.ui.theme import COLORS, FONTS, SPACING, SIZES


class ClassConfigMixin:
    CLASS_COLOR_PALETTE = [
        "#22c55e",
        "#3b82f6",
        "#f97316",
        "#e11d48",
        "#8b5cf6",
        "#14b8a6",
        "#eab308",
        "#ec4899",
        "#06b6d4",
        "#84cc16",
        "#f43f5e",
        "#6366f1",
    ]

    def _category_color_for_index(self, index: int) -> str:
        return self.CLASS_COLOR_PALETTE[index % len(self.CLASS_COLOR_PALETTE)]

    def ensure_category_metadata(self):
        for idx, cat in enumerate(self.categories):
            if not cat.get("color"):
                cat["color"] = self._category_color_for_index(idx)
            if not cat.get("supercategory"):
                cat["supercategory"] = "none"

    def category_name_by_id(self) -> Dict[int, str]:
        return {int(cat.get("id", 0)): str(cat.get("name", "obj")) for cat in self.categories}

    def category_color_by_id(self) -> Dict[int, str]:
        self.ensure_category_metadata()
        return {int(cat.get("id", 0)): str(cat.get("color", "#22c55e")) for cat in self.categories}

    def active_class_name(self) -> str:
        manual_var = getattr(self, "manual_class_var", None)
        if manual_var is not None:
            active = manual_var.get().strip()
            if active:
                return active
        if self.target_classes:
            return self.target_classes[0]
        if self.categories:
            return str(self.categories[0].get("name", "object"))
        return "object"

    def active_category_id(self) -> int:
        return self.register_category(self.active_class_name())

    def register_category(self, class_name: str) -> int:
        clean_name = class_name.strip()
        if not clean_name:
            raise ValueError("Nome de classe vazio.")
        if clean_name in self.class_to_category_id:
            return self.class_to_category_id[clean_name]
        next_id = max((cat.get("id", 0) for cat in self.categories), default=0) + 1
        self.class_to_category_id[clean_name] = next_id
        color = self._category_color_for_index(len(self.categories))
        self.categories.append({"id": next_id, "name": clean_name, "color": color, "supercategory": "none"})
        return next_id

    def sync_category_order(self):
        """Mantem o array COCO categories seguindo a ordem visual das classes."""
        if not self.categories:
            return
        order_by_name = {name: index for index, name in enumerate(self.target_classes)}
        self.categories.sort(
            key=lambda cat: (
                order_by_name.get(str(cat.get("name", "")).strip(), len(order_by_name)),
                int(cat.get("id", 0)),
            )
        )

    def parse_classes_text(self, text: str) -> List[str]:
        items = [part.strip() for part in text.split(",")]
        parsed: List[str] = []
        seen = set()
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            parsed.append(item)
        return parsed

    def apply_target_classes(self, classes: List[str]):
        cleaned = [c.strip() for c in classes if c.strip()]
        self.target_classes = []
        seen = set()
        for name in cleaned:
            if name in seen:
                continue
            seen.add(name)
            self.target_classes.append(name)
        for cname in self.target_classes:
            self.register_category(cname)
        self.sync_category_order()
        self.ensure_category_metadata()

        self.uses_text_prompt = False
        if self.model is not None:
            print("[INFO] Modelo configurado para aceitar qualquer deteccao; classes da UI serao usadas como rotulos.")

        if getattr(self, "target_classes_var", None) is not None:
            self.target_classes_var.set(", ".join(self.target_classes))
        if getattr(self, "manual_class_var", None) is not None:
            current_manual = self.manual_class_var.get().strip()
            if not current_manual or current_manual not in self.target_classes:
                self.manual_class_var.set(self.target_classes[0] if self.target_classes else "")
        self._class_panel_snapshot = None
        self.update_class_panel(force=True)
        self.autosave_classes()

    def apply_target_classes_from_ui(self):
        raw = self.target_classes_var.get() if self.target_classes_var is not None else ""
        parsed = self.parse_classes_text(raw)
        if not parsed:
            print("[AVISO] Informe ao menos uma classe (ex: car, bus, person).")
            return
        self.apply_target_classes(parsed)
        print(f"[INFO] Classes alvo atualizadas: {self.target_classes}")
        self.update_status()

    def autosave_classes(self):
        """Persiste categorias/labels quando a UI de classes muda."""
        if not hasattr(self, "images") or not hasattr(self, "annotations"):
            return
        if not hasattr(self, "write_annotations"):
            return
        try:
            self.write_annotations()
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[AVISO] Falha ao salvar labels/classes automaticamente: {exc}")

    def set_active_class(self, class_name: str, *, apply_to_selection: bool = True):
        clean_name = class_name.strip()
        if not clean_name:
            return
        category_id = self.register_category(clean_name)
        manual_var = getattr(self, "manual_class_var", None)
        if manual_var is not None:
            manual_var.set(clean_name)

        det = self.get_selected_detection() if apply_to_selection else None
        if det is not None:
            self.push_undo_state("alterar classe")
            old_id = det.category_id
            det.category_id = category_id
            old_name = self.category_name_by_id().get(old_id, str(old_id))
            print(f"[INFO] Classe da caixa atualizada: {old_name} -> {clean_name}.")
            self.update_display()
            return

        print(f"[INFO] Classe ativa: {clean_name}.")
        self.update_class_panel()
        self.update_status()

    def select_class_by_index(self, index: int):
        if index < 0 or index >= len(self.target_classes):
            return
        self.set_active_class(self.target_classes[index])

    def on_class_shortcut(self, event):
        widget = self.window.focus_get()
        if isinstance(widget, tk.Entry):
            return
        key = getattr(event, "char", "")
        if not key.isdigit() or key == "0":
            return
        self.select_class_by_index(int(key) - 1)

    # ── gestão de classes ──────────────────────────────────────────

    def remove_class(self, name: str):
        if len(self.target_classes) <= 1:
            return
        next_classes = [c for c in self.target_classes if c != name]
        self.apply_target_classes(next_classes)
        if getattr(self, "canvas", None):
            self.update_status()

    def move_class(self, class_name: str, direction: int):
        """Move uma classe na ordem ativa; indice 0 segue sendo usado nas deteccoes do modelo."""
        if class_name not in self.target_classes:
            return
        index = self.target_classes.index(class_name)
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.target_classes):
            return
        next_classes = list(self.target_classes)
        next_classes[index], next_classes[new_index] = next_classes[new_index], next_classes[index]
        current_active = self.active_class_name()
        self.apply_target_classes(next_classes)
        if getattr(self, "manual_class_var", None) is not None:
            self.manual_class_var.set(current_active if current_active in next_classes else next_classes[0])
        self._class_panel_snapshot = None
        self.update_class_panel(force=True)
        if getattr(self, "canvas", None):
            self.update_status()

    def cycle_class_color(self, name: str):
        cat_id = self.class_to_category_id.get(name)
        if cat_id is None:
            return
        for cat in self.categories:
            if cat.get("id") == cat_id:
                current = cat.get("color", self.CLASS_COLOR_PALETTE[0])
                try:
                    idx = self.CLASS_COLOR_PALETTE.index(current)
                except ValueError:
                    idx = -1
                cat["color"] = self.CLASS_COLOR_PALETTE[(idx + 1) % len(self.CLASS_COLOR_PALETTE)]
                break
        self._class_panel_snapshot = None
        self.update_class_panel(force=True)
        if getattr(self, "canvas", None):
            self.update_display()

    def _add_new_class(self, name: str):
        name = name.strip()
        if not name or name in self.target_classes:
            self._class_panel_editing = False
            self.update_class_panel(force=True)
            return
        self._class_panel_editing = False
        self.apply_target_classes(list(self.target_classes) + [name])
        if getattr(self, "manual_class_var", None):
            self.manual_class_var.set(name)
        if getattr(self, "canvas", None):
            self.update_status()

    # ── painel de classes ──────────────────────────────────────────

    def update_class_panel(self, *, force: bool = False):
        panel = getattr(self, "classes_panel", None)
        if panel is None:
            return
        if getattr(self, "_class_panel_editing", False) and not force:
            return

        self.ensure_category_metadata()
        active_name = self.active_class_name()
        frame_counts: Dict[int, int] = {}
        for det in list(getattr(self, "current_detections", [])) + list(getattr(self, "manual_detections", [])):
            frame_counts[det.category_id] = frame_counts.get(det.category_id, 0) + 1

        color_by_id = self.category_color_by_id()
        snapshot = (
            tuple(self.target_classes),
            active_name,
            tuple(sorted(frame_counts.items())),
            tuple((cat.get("id"), cat.get("name"), cat.get("color")) for cat in self.categories),
        )
        if not force and snapshot == getattr(self, "_class_panel_snapshot", None):
            return
        self._class_panel_snapshot = snapshot

        for child in panel.winfo_children():
            child.destroy()

        for idx, class_name in enumerate(self.target_classes):
            category_id = self.register_category(class_name)
            cat_color = color_by_id.get(category_id, "#22c55e")
            is_active = class_name == active_name
            count = frame_counts.get(category_id, 0)
            self._build_class_tag(panel, idx, class_name, cat_color, is_active, count)

        self._build_add_class_button(panel)

    def _build_class_tag(self, panel, idx: int, class_name: str, color: str, is_active: bool, count: int):
        tag_bg = color if is_active else self.theme["input_bg"]
        tag_fg = COLORS["fg_light"] if is_active else self.theme["text"]

        tag = tk.Frame(
            panel,
            bg=tag_bg,
            highlightbackground=color,
            highlightthickness=1,
            bd=0,
        )
        tag.pack(fill=tk.X, padx=0, pady=(0, SPACING["sm"]))
        tag.columnconfigure(1, weight=1)

        dot = tk.Button(
            tag,
            text="  ",
            bg=color,
            activebackground=color,
            bd=0, relief=tk.FLAT, cursor="hand2",
            highlightthickness=0,
            command=lambda n=class_name: self.cycle_class_color(n),
        )
        dot.grid(row=0, column=0, sticky="nsw", padx=(0, SPACING["xs"]))

        name_btn = tk.Button(
            tag,
            text=f"{idx + 1}  {class_name}  ({count})",
            font=FONTS["tag"],
            padx=SPACING["sm"], pady=SPACING["sm"],
            bd=0, relief=tk.FLAT, cursor="hand2",
            bg=tag_bg, fg=tag_fg,
            activebackground=color, activeforeground=COLORS["fg_light"],
            highlightthickness=0,
            anchor="w",
            command=lambda n=class_name: self.set_active_class(n),
        )
        name_btn.grid(row=0, column=1, sticky="ew")

        if len(self.target_classes) > 1:
            up_btn = tk.Button(
                tag,
                text="↑",
                font=FONTS["tag"],
                padx=SPACING["sm"], pady=SPACING["sm"],
                bd=0, relief=tk.FLAT,
                cursor="hand2" if idx > 0 else "arrow",
                bg=self.theme["neutral"], fg=self.theme["text"],
                activebackground=self.theme["neutral_active"], activeforeground=self.theme["text"],
                disabledforeground=COLORS["muted"],
                highlightthickness=0,
                state=(tk.NORMAL if idx > 0 else tk.DISABLED),
                command=lambda n=class_name: self.move_class(n, -1),
            )
            up_btn.grid(row=0, column=2, sticky="e", padx=(SPACING["sm"], 0))
            down_btn = tk.Button(
                tag,
                text="↓",
                font=FONTS["tag"],
                padx=SPACING["sm"], pady=SPACING["sm"],
                bd=0, relief=tk.FLAT,
                cursor="hand2" if idx < len(self.target_classes) - 1 else "arrow",
                bg=self.theme["neutral"], fg=self.theme["text"],
                activebackground=self.theme["neutral_active"], activeforeground=self.theme["text"],
                disabledforeground=COLORS["muted"],
                highlightthickness=0,
                state=(tk.NORMAL if idx < len(self.target_classes) - 1 else tk.DISABLED),
                command=lambda n=class_name: self.move_class(n, 1),
            )
            down_btn.grid(row=0, column=3, sticky="e", padx=(SPACING["xs"], 0))

        remove_state = tk.NORMAL if len(self.target_classes) > 1 else tk.DISABLED
        remove_btn = tk.Button(
            tag,
            text="Remover",
            font=FONTS["tag"],
            padx=SPACING["sm"], pady=SPACING["sm"],
            bd=0, relief=tk.FLAT,
            cursor="hand2" if len(self.target_classes) > 1 else "arrow",
            bg=self.theme["danger"], fg=COLORS["fg_light"],
            activebackground=self.theme["danger"], activeforeground=COLORS["fg_light"],
            disabledforeground=COLORS["disabled_fg"],
            highlightthickness=0,
            state=remove_state,
            command=lambda n=class_name: self.remove_class(n),
        )
        remove_btn.grid(row=0, column=4, sticky="e", padx=(SPACING["sm"], 0))

    def _build_add_class_button(self, panel):
        btn = tk.Button(
            panel,
            text="+ Nova classe",
            font=FONTS["button"],
            padx=SIZES["btn_pad_x"], pady=SIZES["btn_pad_y"],
            bd=0, relief=tk.FLAT, cursor="hand2",
            bg=self.theme["neutral"], fg=self.theme["text"],
            activebackground=self.theme["neutral_active"], activeforeground=self.theme["text"],
            highlightthickness=1, highlightbackground=self.theme["border"],
            anchor="w",
            command=lambda: self._show_add_class_entry(panel),
        )
        btn.pack(fill=tk.X, pady=(0, SPACING["sm"]))

    def _show_add_class_entry(self, panel):
        if getattr(self, "_class_panel_editing", False):
            return
        self._class_panel_editing = True

        children = panel.winfo_children()
        if children:
            children[-1].destroy()

        entry_var = tk.StringVar()

        wrap = tk.Frame(
            panel,
            bg=self.theme["input_bg"],
            highlightbackground=self.theme["accent"],
            highlightthickness=1, bd=0,
        )
        wrap.pack(fill=tk.X, pady=(0, SPACING["sm"]))

        row = tk.Frame(wrap, bg=self.theme["input_bg"])
        row.pack(fill=tk.X, expand=True)

        entry = tk.Entry(
            row,
            textvariable=entry_var,
            font=FONTS["body"],
            bg=self.theme["input_bg"], fg=self.theme["text"],
            insertbackground=self.theme["text"],
            relief=tk.FLAT, bd=SIZES["input_pad"],
            highlightthickness=0,
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        add_btn = tk.Button(
            row,
            text="Adicionar",
            font=FONTS["tag"],
            padx=SPACING["sm"], pady=SPACING["sm"],
            bd=0, relief=tk.FLAT, cursor="hand2",
            bg=self.theme["primary"], fg=COLORS["fg_light"],
            activebackground=self.theme["primary_active"], activeforeground=COLORS["fg_light"],
            highlightthickness=0,
            command=lambda: confirm(),
        )
        add_btn.pack(side=tk.LEFT, padx=(SPACING["xs"], 0))

        cancel_btn = tk.Button(
            row,
            text="Cancelar",
            font=FONTS["tag"],
            padx=SPACING["sm"], pady=SPACING["sm"],
            bd=0, relief=tk.FLAT, cursor="hand2",
            bg=self.theme["neutral"], fg=self.theme["text"],
            activebackground=self.theme["neutral_active"], activeforeground=self.theme["text"],
            highlightthickness=0,
            command=lambda: cancel(),
        )
        cancel_btn.pack(side=tk.LEFT, padx=(SPACING["xs"], 0))

        entry.focus_set()

        def confirm(_=None):
            self._add_new_class(entry_var.get())

        def cancel(_=None):
            self._class_panel_editing = False
            self._class_panel_snapshot = None
            self.update_class_panel(force=True)

        entry.bind("<Return>", confirm)
        entry.bind("<Escape>", cancel)
