from app.annotation.shared import *


class SelectionEditMixin:
    def validate_selected_detection(self):
        """Limpa selecao se o indice estiver invalido."""
        if self.get_selected_detection() is None:
            self.selected_detection = None

    def get_selected_detection(self) -> Optional[Detection]:
        """Retorna a detection selecionada (se existir)."""
        if self.selected_detection is None:
            return None
        source, idx = self.selected_detection
        dets = self.manual_detections if source == "manual" else self.current_detections
        if 0 <= idx < len(dets):
            return dets[idx]
        return None

    @staticmethod
    def bbox_close(stored_bbox, bbox: np.ndarray, tol: float = 1.0) -> bool:
        """Compara bboxes com tolerancia."""
        if stored_bbox is None:
            return False
        arr = np.array(stored_bbox, dtype=np.float32)
        return np.allclose(arr, bbox, atol=tol)

    def find_detection_at(self, x: int, y: int) -> Optional[Tuple[str, int]]:
        """Retorna (source, idx) da bbox que contem o ponto."""
        candidates: List[Tuple[float, str, int]] = []
        for idx, det in enumerate(self.manual_detections):
            x1, y1, x2, y2 = det.original_bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                area = float(max(x2 - x1, 0.0) * max(y2 - y1, 0.0))
                candidates.append((area, "manual", idx))
        for idx, det in enumerate(self.current_detections):
            x1, y1, x2, y2 = det.original_bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                area = float(max(x2 - x1, 0.0) * max(y2 - y1, 0.0))
                candidates.append((area, "model", idx))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        _, source, idx = candidates[0]
        return (source, idx)

    def select_detection_at(self, x: int, y: int):
        """Seleciona a bbox clicada para editar o ID."""
        hit = self.find_detection_at(x, y)
        if hit is None:
            self.selected_detection = None
            self.update_display()
            return
        self.selected_detection = hit
        det = self.get_selected_detection()
        if det is not None:
            self.manual_id_var.set(str(det.track_id))
        self.update_display()

    def apply_manual_id_to_selection(self):
        """Aplica o ID digitado a bbox selecionada."""
        if self.selected_detection is None:
            print("[AVISO] Nenhuma caixa selecionada para editar.")
            return
        new_id = self.consume_manual_id_override()
        if new_id is None:
            return
        det = self.get_selected_detection()
        if det is None:
            print("[AVISO] Selecao invalida. Clique novamente na caixa.")
            self.selected_detection = None
            return
        old_id = det.track_id
        if old_id == new_id:
            print("[INFO] ID selecionado ja e o mesmo.")
            return
        det.track_id = new_id
        if det.source == "model" and det.internal_id is not None:
            self.tracker_id_map[det.internal_id] = new_id
        self.update_track_history_for_edit(old_id, new_id, det.original_bbox)
        self.update_recent_tracks_for_edit(old_id, new_id, det.original_bbox)
        if det.source == "manual":
            if old_id in self.manual_track_memory:
                del self.manual_track_memory[old_id]
            self.manual_track_memory[new_id] = {"bbox": det.original_bbox.copy()}
        print(f"[INFO] Track ID atualizado: {old_id} -> {new_id}.")
        self.update_display()

    def update_track_history_for_edit(self, old_id: int, new_id: int, bbox: np.ndarray):
        """Atualiza track_history ao trocar track_id."""
        old_entries = self.track_history.get(old_id, [])
        if old_entries:
            filtered = [
                entry
                for entry in old_entries
                if not (entry.get("frame") == self.frame_index and self.bbox_close(entry.get("bbox"), bbox))
            ]
            if filtered:
                self.track_history[old_id] = filtered
            else:
                self.track_history.pop(old_id, None)
        entries = self.track_history.setdefault(new_id, [])
        exists = any(
            entry.get("frame") == self.frame_index and self.bbox_close(entry.get("bbox"), bbox) for entry in entries
        )
        if not exists:
            entries.append({"frame": self.frame_index, "bbox": bbox.tolist()})

    def update_recent_tracks_for_edit(self, old_id: int, new_id: int, bbox: np.ndarray):
        """Atualiza recent_tracks no frame atual."""
        for frame_data in self.recent_tracks:
            if frame_data.get("frame") != self.frame_index:
                continue
            for tr in frame_data.get("tracks", []):
                if tr.get("id") == old_id and self.bbox_close(tr.get("bbox"), bbox):
                    tr["id"] = new_id

