from app.annotation.shared import *


class SelectionEditMixin:
    def push_undo_state(self, reason: str = ""):
        """Salva estado leve do frame atual para Ctrl+Z."""
        if self.current_frame is None:
            return
        snapshot = {
            "reason": reason,
            "current_detections": [self.clone_detection(det) for det in self.current_detections],
            "manual_detections": [self.clone_detection(det) for det in self.manual_detections],
            "selected_detection": self.selected_detection,
            "track_history": {
                tid: [dict(entry) for entry in entries] for tid, entries in self.track_history.items()
            },
            "recent_tracks": [
                {
                    "frame": item.get("frame"),
                    "tracks": [
                        {"id": track.get("id"), "bbox": np.array(track.get("bbox"), dtype=np.float32).copy()}
                        for track in item.get("tracks", [])
                    ],
                }
                for item in self.recent_tracks
            ],
            "manual_track_memory": {
                tid: {"bbox": value["bbox"].copy()} for tid, value in self.manual_track_memory.items()
            },
        }
        self.undo_stack.append(snapshot)

    def undo_last_action(self):
        """Restaura o ultimo estado de anotacoes do frame atual."""
        if not self.undo_stack:
            print("[INFO] Nada para desfazer.")
            return
        snapshot = self.undo_stack.pop()
        self.current_detections = [self.clone_detection(det) for det in snapshot["current_detections"]]
        self.manual_detections = [self.clone_detection(det) for det in snapshot["manual_detections"]]
        self.selected_detection = snapshot["selected_detection"]
        self.track_history = {
            tid: [dict(entry) for entry in entries] for tid, entries in snapshot["track_history"].items()
        }
        self.recent_tracks = deque(snapshot["recent_tracks"], maxlen=self.history_window)
        self.manual_track_memory = snapshot["manual_track_memory"]
        print(f"[INFO] Desfeito: {snapshot.get('reason') or 'ultima acao'}.")
        self.update_display(refresh_status=True)

    def remove_detection_from_runtime_state(self, det: Detection):
        """Remove referencias da deteccao apagada do estado temporario do frame."""
        if det.track_id is None:
            return
        if det.source == "manual":
            memory = self.manual_track_memory.get(det.track_id)
            if memory is not None and self.bbox_close(memory.get("bbox"), det.original_bbox):
                self.manual_track_memory.pop(det.track_id, None)

        entries = self.track_history.get(det.track_id, [])
        filtered_entries = [
            entry
            for entry in entries
            if not (entry.get("frame") == self.frame_index and self.bbox_close(entry.get("bbox"), det.original_bbox))
        ]
        if filtered_entries:
            self.track_history[det.track_id] = filtered_entries
        else:
            self.track_history.pop(det.track_id, None)

        filtered_recent_tracks = []
        for frame_data in self.recent_tracks:
            if frame_data.get("frame") != self.frame_index:
                filtered_recent_tracks.append(frame_data)
                continue
            tracks = [
                track
                for track in frame_data.get("tracks", [])
                if not (track.get("id") == det.track_id and self.bbox_close(track.get("bbox"), det.original_bbox))
            ]
            if tracks:
                filtered_recent_tracks.append({"frame": frame_data.get("frame"), "tracks": tracks})
        self.recent_tracks = deque(filtered_recent_tracks, maxlen=self.history_window)

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
            self.update_display(refresh_status=True)
            return
        self.selected_detection = hit
        det = self.get_selected_detection()
        if det is not None:
            self.manual_id_var.set(str(det.track_id))
            class_name = self.category_name_by_id().get(det.category_id)
            manual_var = getattr(self, "manual_class_var", None)
            if class_name and manual_var is not None:
                manual_var.set(class_name)
            self.update_class_panel()
        self.update_display(refresh_status=True)

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
        self.push_undo_state("editar ID")
        det.track_id = new_id
        if det.source == "model" and det.internal_id is not None:
            self.tracker_id_map[(det.category_id, det.internal_id)] = new_id
        self.update_track_history_for_edit(old_id, new_id, det.original_bbox)
        self.update_recent_tracks_for_edit(old_id, new_id, det.original_bbox)
        if det.source == "manual":
            if old_id in self.manual_track_memory:
                del self.manual_track_memory[old_id]
            self.manual_track_memory[new_id] = {"bbox": det.original_bbox.copy()}
        print(f"[INFO] Track ID atualizado: {old_id} -> {new_id}.")
        self.update_display(refresh_status=True)

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
