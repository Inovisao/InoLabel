import sys

from app.annotation.shared import *
from app.ui.theme.palette import CLASS_COLORS


class ClassServiceMixin:
    CLASS_COLOR_PALETTE = CLASS_COLORS  # kept for external compatibility

    # ── colors & metadata ──────────────────────────────────────────

    def _category_color_for_index(self, index: int) -> str:
        return CLASS_COLORS[index % len(CLASS_COLORS)]

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

    # ── active class ───────────────────────────────────────────────

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

    # ── category registration ──────────────────────────────────────

    def register_category(self, class_name: str) -> int:
        clean_name = class_name.strip()
        if not clean_name:
            raise ValueError("Nome de classe vazio.")
        if clean_name in self.class_to_category_id:
            return self.class_to_category_id[clean_name]
        used_ids = {int(cat.get("id", 0)) for cat in self.categories}
        preferred_id = None
        if clean_name in getattr(self, "target_classes", []):
            preferred_id = list(self.target_classes).index(clean_name) + 1
        next_id = preferred_id if preferred_id is not None and preferred_id not in used_ids else max(used_ids, default=0) + 1
        self.class_to_category_id[clean_name] = next_id
        color = self._category_color_for_index(len(self.categories))
        self.categories.append({"id": next_id, "name": clean_name, "color": color, "supercategory": "none"})
        return next_id

    def normalize_category_ids(self) -> Dict[int, int]:
        """Keeps categories/annotations/caches with IDs 1..N following target_classes order."""
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

    # ── internal remapping ────────────────────────────────────────

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

    @staticmethod
    def _remap_detection_list_by_category(
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
            getattr(self, "current_detections", []), remap, valid_ids,
        )
        self.manual_detections = self._remap_detection_list_by_category(
            getattr(self, "manual_detections", []), remap, valid_ids,
        )
        if hasattr(self, "current_obb_detections"):
            self.current_obb_detections = self.current_detections
        if hasattr(self, "manual_obb_detections"):
            self.manual_obb_detections = self.manual_detections
        for record in getattr(self, "saved_records", []):
            record["detections"] = self._remap_detection_list_by_category(
                record.get("detections", []), remap, valid_ids,
            )
        snapshot = getattr(self, "live_snapshot", None)
        if snapshot is not None:
            for key in ("detections", "current", "current_detections"):
                if key in snapshot:
                    snapshot[key] = self._remap_detection_list_by_category(snapshot[key], remap, valid_ids)
            for key in ("manual_detections", "manual"):
                if key in snapshot:
                    snapshot[key] = self._remap_detection_list_by_category(snapshot[key], remap, valid_ids)
        self.undo_stack = deque(
            (
                {
                    **s,
                    **{
                        key: self._remap_detection_list_by_category(s[key], remap, valid_ids)
                        for key in ("current_detections", "manual_detections", "current", "manual")
                        if key in s
                    },
                    "selected_detection": None,
                }
                for s in getattr(self, "undo_stack", [])
            ),
            maxlen=getattr(self, "max_undo_states", 40),
        )
        self._remap_tracker_state_by_category(remap, valid_ids)

    def _remap_tracker_state_by_category(self, remap: Dict[int, int], valid_ids: set):
        tracker_id_map = getattr(self, "tracker_id_map", None)
        if tracker_id_map is not None:
            next_map = {}
            for key, track_id in tracker_id_map.items():
                if not isinstance(key, tuple) or len(key) != 2:
                    continue
                category_id, internal_id = key
                new_category_id = remap.get(int(category_id), int(category_id))
                if new_category_id in valid_ids:
                    next_map[(new_category_id, int(internal_id))] = track_id
            self.tracker_id_map = next_map
        if any(old_id != new_id for old_id, new_id in remap.items()):
            tracker = getattr(self, "multiclass_tracker", None)
            if tracker is not None:
                tracker.reset()

    # ── ordering and parsing ──────────────────────────────────────

    def sync_category_order(self):
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

    # ── apply classes ─────────────────────────────────────────────

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
        if not hasattr(self, "images") or not hasattr(self, "annotations"):
            return
        if not hasattr(self, "write_annotations"):
            return
        try:
            self.write_annotations()
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[AVISO] Falha ao salvar labels/classes automaticamente: {exc}")

    # ── selection and shortcuts ───────────────────────────────────

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
        if isinstance(widget, (tk.Entry, tk.Text)):
            return
        key = getattr(event, "char", "")
        if not key.isdigit() or key == "0":
            return
        self.select_class_by_index(int(key) - 1)

    # ── class management ──────────────────────────────────────────

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
        compat_module = sys.modules.get("app.annotation.state.class_config")
        confirm_box = getattr(compat_module, "messagebox", messagebox)
        if not confirm_box.askyesno("Remover classe", prompt):
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
        if hasattr(self, "selected_obb"):
            self.selected_obb = None

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
        if hasattr(self, "current_obb_detections"):
            self.current_obb_detections = self.current_detections
        if hasattr(self, "manual_obb_detections"):
            self.manual_obb_detections = self.manual_detections
        for record in getattr(self, "saved_records", []):
            record["detections"] = self._filter_detections_by_category(record.get("detections", []), category_id)
        snapshot = getattr(self, "live_snapshot", None)
        if snapshot is not None:
            for key in ("detections", "current", "current_detections"):
                if key in snapshot:
                    snapshot[key] = self._filter_detections_by_category(snapshot[key], category_id)
            for key in ("manual_detections", "manual"):
                if key in snapshot:
                    snapshot[key] = self._filter_detections_by_category(snapshot[key], category_id)
        self.undo_stack = deque(
            (
                {
                    **s,
                    **{
                        key: self._filter_detections_by_category(s[key], category_id)
                        for key in ("current_detections", "manual_detections", "current", "manual")
                        if key in s
                    },
                    "selected_detection": None,
                }
                for s in getattr(self, "undo_stack", [])
            ),
            maxlen=getattr(self, "max_undo_states", 40),
        )

    def move_class(self, class_name: str, direction: int):
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
