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

    def normalize_category_ids(self) -> Dict[int, int]:
        """Mantem categories/annotations/caches com IDs 1..N seguindo target_classes."""
        cleaned_classes = []
        seen = set()
        for class_name in self.target_classes:
            name = str(class_name).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            cleaned_classes.append(name)
        self.target_classes = cleaned_classes

        old_by_name: Dict[str, int] = {}
        metadata_by_name: Dict[str, dict] = {}
        for idx, cat in enumerate(self.categories):
            name = str(cat.get("name", "")).strip()
            if not name or name in metadata_by_name:
                continue
            metadata = dict(cat)
            metadata["name"] = name
            if not metadata.get("color"):
                metadata["color"] = self._category_color_for_index(idx)
            if not metadata.get("supercategory"):
                metadata["supercategory"] = "none"
            metadata_by_name[name] = metadata
            try:
                old_by_name[name] = int(cat.get("id"))
            except (TypeError, ValueError):
                pass

        for name, category_id in self.class_to_category_id.items():
            clean_name = str(name).strip()
            if not clean_name or clean_name in old_by_name:
                continue
            try:
                old_by_name[clean_name] = int(category_id)
            except (TypeError, ValueError):
                pass

        remap: Dict[int, int] = {}
        next_categories: List[dict] = []
        self.class_to_category_id = {}
        for idx, name in enumerate(self.target_classes):
            new_id = idx + 1
            old_id = old_by_name.get(name)
            if old_id is not None:
                remap[old_id] = new_id
            metadata = dict(metadata_by_name.get(name, {}))
            metadata["id"] = new_id
            metadata["name"] = name
            metadata.setdefault("color", self._category_color_for_index(idx))
            metadata.setdefault("supercategory", "none")
            next_categories.append(metadata)
            self.class_to_category_id[name] = new_id

        self.categories = next_categories
        self._remap_annotations_by_category(remap)
        self._remap_detection_caches_by_category(remap, set(self.class_to_category_id.values()))
        return remap

    def _remap_annotations_by_category(self, remap: Dict[int, int]):
        next_annotations = []
        valid_ids = set(self.class_to_category_id.values())
        for ann in getattr(self, "annotations", []):
            try:
                old_id = int(ann.get("category_id"))
            except (TypeError, ValueError):
                continue
            new_id = remap.get(old_id, old_id)
            if new_id not in valid_ids:
                continue
            if new_id != old_id:
                ann = dict(ann)
                ann["category_id"] = new_id
            next_annotations.append(ann)
        self.annotations = next_annotations

    def _remap_detection_list_by_category(
        self,
        detections: List[Detection],
        remap: Dict[int, int],
        valid_ids: set,
    ) -> List[Detection]:
        next_detections = []
        for det in detections:
            old_id = int(det.category_id)
            new_id = remap.get(old_id, old_id)
            if new_id not in valid_ids:
                continue
            det.category_id = new_id
            next_detections.append(det)
        return next_detections

    def _remap_detection_caches_by_category(self, remap: Dict[int, int], valid_ids: set):
        self.current_detections = self._remap_detection_list_by_category(
            getattr(self, "current_detections", []),
            remap,
            valid_ids,
        )
        self.manual_detections = self._remap_detection_list_by_category(
            getattr(self, "manual_detections", []),
            remap,
            valid_ids,
        )

        for record in getattr(self, "saved_records", []):
            record["detections"] = self._remap_detection_list_by_category(
                record.get("detections", []),
                remap,
                valid_ids,
            )

        snapshot = getattr(self, "live_snapshot", None)
        if snapshot is not None:
            snapshot["detections"] = self._remap_detection_list_by_category(
                snapshot.get("detections", []),
                remap,
                valid_ids,
            )
            snapshot["manual_detections"] = self._remap_detection_list_by_category(
                snapshot.get("manual_detections", []),
                remap,
                valid_ids,
            )

        self.undo_stack = deque(
            (
                {
                    **snapshot,
                    "current_detections": self._remap_detection_list_by_category(
                        snapshot.get("current_detections", []),
                        remap,
                        valid_ids,
                    ),
                    "manual_detections": self._remap_detection_list_by_category(
                        snapshot.get("manual_detections", []),
                        remap,
                        valid_ids,
                    ),
                    "selected_detection": None,
                }
                for snapshot in getattr(self, "undo_stack", [])
            ),
            maxlen=getattr(self, "max_undo_states", 40),
        )
        self._remap_tracker_state_by_category(remap, valid_ids)

    def _remap_tracker_state_by_category(self, remap: Dict[int, int], valid_ids: set):
        tracker_id_map = getattr(self, "tracker_id_map", None)
        if tracker_id_map is not None:
            next_tracker_id_map = {}
            for key, track_id in tracker_id_map.items():
                if not isinstance(key, tuple) or len(key) != 2:
                    continue
                category_id, internal_id = key
                new_category_id = remap.get(int(category_id), int(category_id))
                if new_category_id in valid_ids:
                    next_tracker_id_map[(new_category_id, int(internal_id))] = track_id
            self.tracker_id_map = next_tracker_id_map

        if any(old_id != new_id for old_id, new_id in remap.items()):
            tracker = getattr(self, "multiclass_tracker", None)
            if tracker is not None:
                tracker.reset()

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
        previous_snapshot = (
            tuple(getattr(self, "target_classes", [])),
            tuple((cat.get("id"), cat.get("name"), cat.get("color")) for cat in getattr(self, "categories", [])),
            tuple(sorted(getattr(self, "class_to_category_id", {}).items())),
        )
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
        self.normalize_category_ids()
        next_snapshot = (
            tuple(self.target_classes),
            tuple((cat.get("id"), cat.get("name"), cat.get("color")) for cat in self.categories),
            tuple(sorted(self.class_to_category_id.items())),
        )
        changed = next_snapshot != previous_snapshot

        self.uses_text_prompt = False
        if self.model is not None:
            print("[INFO] Modelo configurado para aceitar qualquer deteccao; classes da UI serao usadas como rotulos.")

        if getattr(self, "target_classes_var", None) is not None:
            self.target_classes_var.set(", ".join(self.target_classes))
        if getattr(self, "manual_class_var", None) is not None:
            current_manual = self.manual_class_var.get().strip()
            if not current_manual or current_manual not in self.target_classes:
                self.manual_class_var.set(self.target_classes[0] if self.target_classes else "")
        if changed:
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
            self.update_display(refresh_status=True)
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
        if name not in self.target_classes:
            return

        cat_id = self.category_id_for_class_name(name)
        saved_count = sum(1 for ann in self.annotations if ann.get("category_id") == cat_id) if cat_id else 0
        frame_count = self._remove_class_runtime_count(cat_id)

        prompt = f'Remover a classe "{name}"?'
        if saved_count or frame_count:
            prompt += (
                "\n\nIsso excluira "
                f"{saved_count} anotacao(es) salva(s) e "
                f"{frame_count} deteccao(oes) em memoria com essa classe."
            )
        if not messagebox.askyesno("Remover classe", prompt):
            return

        if cat_id is not None:
            self.annotations = [ann for ann in self.annotations if ann.get("category_id") != cat_id]
            self.categories = [cat for cat in self.categories if cat.get("id") != cat_id]
            self.remove_category_mapping(name, cat_id)
            self._remove_class_from_detection_caches(cat_id)

        next_classes = [c for c in self.target_classes if c != name]
        self.apply_target_classes(next_classes)
        self.write_annotations()
        self.sync_export_metadata()
        self.selected_detection = None

        if getattr(self, "canvas", None):
            self.update_display()
            self.update_status()

    def category_id_for_class_name(self, name: str) -> Optional[int]:
        cat_id = self.class_to_category_id.get(name)
        if cat_id is not None:
            return int(cat_id)
        for cat in self.categories:
            if str(cat.get("name", "")).strip() == name:
                try:
                    return int(cat.get("id"))
                except (TypeError, ValueError):
                    return None
        return None

    def remove_category_mapping(self, name: str, category_id: int):
        stale_names = []
        for class_name, mapped_id in self.class_to_category_id.items():
            try:
                is_same_category = int(mapped_id) == category_id
            except (TypeError, ValueError):
                is_same_category = False
            if class_name == name or is_same_category:
                stale_names.append(class_name)
        for class_name in stale_names:
            self.class_to_category_id.pop(class_name, None)

    @staticmethod
    def _filter_detections_by_category(detections: List[Detection], category_id: Optional[int]) -> List[Detection]:
        if category_id is None:
            return list(detections)
        return [det for det in detections if det.category_id != category_id]

    def _remove_class_runtime_count(self, category_id: Optional[int]) -> int:
        if category_id is None:
            return 0
        count = 0
        for attr in ("current_detections", "manual_detections"):
            count += sum(1 for det in getattr(self, attr, []) if det.category_id == category_id)
        for record in getattr(self, "saved_records", []):
            count += sum(1 for det in record.get("detections", []) if det.category_id == category_id)
        snapshot = getattr(self, "live_snapshot", None)
        if snapshot is not None:
            count += sum(1 for det in snapshot.get("detections", []) if det.category_id == category_id)
            count += sum(1 for det in snapshot.get("manual_detections", []) if det.category_id == category_id)
        return count

    def _remove_class_from_detection_caches(self, category_id: int):
        self.current_detections = self._filter_detections_by_category(self.current_detections, category_id)
        self.manual_detections = self._filter_detections_by_category(self.manual_detections, category_id)

        for record in getattr(self, "saved_records", []):
            record["detections"] = self._filter_detections_by_category(record.get("detections", []), category_id)

        snapshot = getattr(self, "live_snapshot", None)
        if snapshot is not None:
            snapshot["detections"] = self._filter_detections_by_category(snapshot.get("detections", []), category_id)
            snapshot["manual_detections"] = self._filter_detections_by_category(
                snapshot.get("manual_detections", []),
                category_id,
            )

        self.undo_stack = deque(
            (
                {
                    **snapshot,
                    "current_detections": self._filter_detections_by_category(
                        snapshot.get("current_detections", []), category_id
                    ),
                    "manual_detections": self._filter_detections_by_category(
                        snapshot.get("manual_detections", []), category_id
                    ),
                    "selected_detection": None,
                }
                for snapshot in getattr(self, "undo_stack", [])
            ),
            maxlen=getattr(self, "max_undo_states", 40),
        )

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
            self.update_display(refresh_status=True)

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
        structure_snapshot = (
            tuple(self.target_classes),
            tuple((cat.get("id"), cat.get("name"), cat.get("color")) for cat in self.categories),
        )
        dynamic_snapshot = (
            active_name,
            tuple(sorted(frame_counts.items())),
        )
        if (
            not force
            and structure_snapshot == getattr(self, "_class_panel_structure_snapshot", None)
            and dynamic_snapshot == getattr(self, "_class_panel_dynamic_snapshot", None)
        ):
            return

        if not force and structure_snapshot == getattr(self, "_class_panel_structure_snapshot", None):
            self._class_panel_dynamic_snapshot = dynamic_snapshot
            self._update_class_tag_widgets(active_name, frame_counts, color_by_id)
            return

        self._class_panel_structure_snapshot = structure_snapshot
        self._class_panel_dynamic_snapshot = dynamic_snapshot
        self._class_panel_snapshot = (structure_snapshot, dynamic_snapshot)
        self._class_tag_widgets = {}

        for child in panel.winfo_children():
            child.destroy()

        for idx, class_name in enumerate(self.target_classes):
            category_id = self.register_category(class_name)
            cat_color = color_by_id.get(category_id, "#22c55e")
            is_active = class_name == active_name
            count = frame_counts.get(category_id, 0)
            self._build_class_tag(panel, idx, class_name, cat_color, is_active, count)

        self._build_add_class_button(panel)

    def _update_class_tag_widgets(self, active_name: str, frame_counts: Dict[int, int], color_by_id: Dict[int, str]):
        widgets_by_name = getattr(self, "_class_tag_widgets", {})
        for idx, class_name in enumerate(self.target_classes):
            widgets = widgets_by_name.get(class_name)
            if not widgets:
                continue
            category_id = self.class_to_category_id.get(class_name, 0)
            color = color_by_id.get(category_id, "#22c55e")
            is_active = class_name == active_name
            count = frame_counts.get(category_id, 0)
            tag_bg = color if is_active else self.theme["input_bg"]
            tag_fg = COLORS["fg_light"] if is_active else self.theme["text"]
            self._config_if_changed(widgets["tag"], bg=tag_bg)
            self._config_if_changed(widgets["name_btn"], text=f"{idx + 1}  {class_name}  ({count})", bg=tag_bg, fg=tag_fg)

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
        self._class_tag_widgets[class_name] = {
            "tag": tag,
            "name_btn": name_btn,
        }

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
