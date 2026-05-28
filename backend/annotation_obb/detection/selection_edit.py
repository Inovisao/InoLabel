from backend.annotation_obb.shared import *


class OBBSelectionEditMixin:
    def clone_obb_detection(self, det: OBBDetection) -> OBBDetection:
        return clone_obb(det)

    def push_undo_state(self, reason: str = ""):
        if self.current_frame is None:
            return
        self.undo_stack.append({
            "reason": reason,
            "current": [clone_obb(det) for det in self.current_obb_detections],
            "manual": [clone_obb(det) for det in self.manual_obb_detections],
            "selected": self.selected_obb,
        })

    def undo_last_action(self):
        if not self.undo_stack:
            print("[INFO] Nada para desfazer.")
            return
        snapshot = self.undo_stack.pop()
        self.current_obb_detections = [clone_obb(det) for det in snapshot["current"]]
        self.manual_obb_detections = [clone_obb(det) for det in snapshot["manual"]]
        self.current_detections = self.current_obb_detections
        self.manual_detections = self.manual_obb_detections
        self.selected_obb = snapshot["selected"]
        self.selected_detection = self.selected_obb
        print(f"[INFO] Desfeito: {snapshot.get('reason') or 'ultima acao OBB'}.")
        self.update_display(refresh_status=True)

    def validate_selected_detection(self):
        if self.get_selected_detection() is None:
            self.selected_obb = None
            self.selected_detection = None

    def get_selected_detection(self) -> Optional[OBBDetection]:
        if self.selected_obb is None:
            return None
        source, idx = self.selected_obb
        dets = self.manual_obb_detections if source == "manual" else self.current_obb_detections
        if 0 <= idx < len(dets):
            return dets[idx]
        return None

    def apply_manual_id_to_selection(self):
        print("[INFO] O modo OBB MVP nao usa IDs de tracking.")

    def remove_detection_from_runtime_state(self, det):
        _ = det
        return None

    def find_detection_at(self, x: int, y: int) -> Optional[Tuple[str, int]]:
        candidates: List[Tuple[float, str, int]] = []
        for source, dets in (("manual", self.manual_obb_detections), ("model", self.current_obb_detections)):
            for idx, det in enumerate(dets):
                lx, ly = global_to_local(x, y, det.cx, det.cy, det.angle)
                if abs(lx) <= det.width / 2.0 and abs(ly) <= det.height / 2.0:
                    candidates.append((det.width * det.height, source, idx))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        _, source, idx = candidates[0]
        return source, idx

    def select_detection_at(self, x: int, y: int):
        hit = self.find_detection_at(x, y)
        self.selected_obb = hit
        self.selected_detection = hit
        det = self.get_selected_detection()
        if det is not None:
            class_name = self.category_name_by_id().get(det.category_id)
            manual_var = getattr(self, "manual_class_var", None)
            if class_name and manual_var is not None:
                manual_var.set(class_name)
            self.update_class_panel()
        self.update_display(refresh_status=True)
