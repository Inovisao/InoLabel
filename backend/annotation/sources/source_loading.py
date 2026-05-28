from backend.annotation.shared import *


class SourceLoadingMixin:
    def load_existing_annotations(self):
        """Carrega anotacoes existentes para continuar de onde parou."""
        annotations_path = getattr(self, "annotations_path", ANNOTATIONS_PATH)
        if not annotations_path.exists():
            return
        try:
            with open(annotations_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[AVISO] Falha ao ler anotacoes existentes: {exc}")
            return
        self.images = data.get("images", [])
        self.annotations = data.get("annotations", [])
        state = data.get("annotation_state", {})
        self.annotation_state = state if isinstance(state, dict) else {}
        cats = data.get("categories")
        if cats:
            self.categories = cats
            self.class_to_category_id = {}
            self.ensure_category_metadata()
            for cat in self.categories:
                name = str(cat.get("name", "")).strip()
                cid = int(cat.get("id", 0))
                if name and cid > 0:
                    self.class_to_category_id[name] = cid
            if not self.target_classes:
                self.target_classes = [cat["name"] for cat in self.categories if cat.get("name")]
            if self.target_classes_var is not None:
                self.target_classes_var.set(", ".join(self.target_classes))
        max_ann_id = max((ann.get("id", 0) for ann in self.annotations), default=0)
        max_img_id = max((img.get("id", 0) for img in self.images), default=0)
        self.annotation_id = max_ann_id + 1
        self.image_id = max_img_id + 1
        max_track = max((ann.get("track_id", 0) or 0 for ann in self.annotations), default=0)
        self.global_track_counter = max(max_track + 1, 1)
        resume_file = self.annotation_state.get("last_active_file_name")
        print(
            f"[INFO] Anotacoes carregadas. imagens={len(self.images)}, "
            f"anotacoes={len(self.annotations)}, prox_image_id={self.image_id}, "
            f"prox_annotation_id={self.annotation_id}, retomada={resume_file or 'auto'}"
        )

    def register_signal_handlers(self):
        """Garante que a janela feche se o processo receber SIGINT/SIGTERM."""
        def handler(signum, frame):
            _ = frame  # unused
            print(f"[INFO] Encerrando por sinal {signum}.")
            self.finish_processing("Processo encerrado pelo sistema.")

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, handler)
            except Exception:  # pylint: disable=broad-except
                pass

    def start_video(self, index: int):
        """Abre o video indicado e prepara para anotacao."""
        if index < 0 or index >= len(self.video_files):
            self.finish_processing("Todas as fontes foram processadas.")
            return

        self._reset_open_source()
        self._reset_model_tracking_state()
        self._prepare_source_state(index)
        self._reset_source_runtime_data()

        first_frame = self._load_first_frame_for_source()
        if first_frame is None:
            self.start_video(index + 1)
            return

        self.enable_controls_after_roi()
        self.process_current_frame(first_frame, advance_index=True, render=False)
        self.restore_saved_annotations_for_current_frame()
        self.update_display(refresh_status=True)

    def finish_current_video(self):
        """Fecha o video atual e segue para o proximo se existir."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        next_index = self.current_video_index + 1
        if next_index < len(self.video_files):
            print(f"[INFO] Fonte concluida: {self.video_name}. Iniciando proxima.")
            self.start_video(next_index)
        else:
            self.finish_processing("Todas as fontes foram processadas.")

    # ===================== ROI & HOMOGRAFIA =====================
