from app.annotation.shared import *
from app.ui.theme import COLORS


class DisplayStatusMixin:
    @staticmethod
    def _set_var_if_changed(var, value: str):
        if var.get() != value:
            var.set(value)

    @staticmethod
    def _config_if_changed(widget, **kwargs):
        updates = {}
        for key, value in kwargs.items():
            try:
                current = widget.cget(key)
            except tk.TclError:
                current = None
            if str(current) != str(value):
                updates[key] = value
        if updates:
            widget.config(**updates)

    def current_review_record(self) -> Optional[dict]:
        """Retorna o registro salvo atualmente em revisao."""
        if self.review_idx is None or not self.saved_records:
            return None
        if self.review_idx < 0 or self.review_idx >= len(self.saved_records):
            return None
        return self.saved_records[self.review_idx]

    def current_deletable_image_path(self) -> Optional[Path]:
        """Retorna a imagem atual que pode ser excluida pelo botao da UI."""
        record = self.current_review_record()
        if record is not None:
            file_name = str(record.get("file_name", "")).strip()
            if not file_name:
                return None
            return self.output_images_dir / file_name
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            return self.current_source_image_path
        return None

    def build_status_message(self) -> str:
        """Mensagem curta para o topo — modo ativo e fonte atual."""
        if self.review_idx is not None and self.saved_records:
            return f"Revisão {self.review_idx + 1}/{len(self.saved_records)} · {self.video_name}"
        if self.pan_mode:
            mode = "Pan ON"
        elif self.annotation_mode:
            mode = "Anotação manual ON"
        elif self.remove_mode:
            mode = "Remoção ON"
        elif self.edit_id_mode and self.tracking_enabled:
            mode = "Editar ID ON"
        else:
            mode = self.task_mode.label
        return f"{mode} · {self.video_name} · Frame {self.frame_index}"

    def update_status(self):
        """Atualiza barra de topo, blocos de status e botões."""
        self._set_var_if_changed(self.info_var, self.build_status_message())
        self.update_class_panel()
        self.update_status_blocks()
        self.update_image_info()
        self.update_annotation_button()
        self.update_remove_button()
        self.update_selection_button()
        self.update_edit_id_button()
        self.update_pan_button()

    def update_status_blocks(self):
        """Popula os cinco blocos da status strip com estado estruturado."""
        if not hasattr(self, "status_source_var"):
            return

        # Bloco 1: fonte + frame
        idx = self.current_video_index + 1
        total = len(self.video_files)
        if self.review_idx is not None and self.saved_records:
            frame_info = f"Rev. {self.review_idx + 1}/{len(self.saved_records)}"
        else:
            frame_info = f"Frame {self.frame_index}"
        self._set_var_if_changed(self.status_source_var, f"{self.video_name}  [{idx}/{total}]  ·  {frame_info}")

        # Bloco 2: ROI
        if self.roi_defined:
            size_str = f" {self.warp_size[0]}×{self.warp_size[1]}" if self.warp_size else ""
            self._set_var_if_changed(self.status_roi_var, f"ROI ✓{size_str}")
            self._config_if_changed(self.status_roi_lbl, fg=COLORS["primary"])
        else:
            pts = len(self.roi_points)
            self._set_var_if_changed(self.status_roi_var, f"ROI {pts}/4 pts")
            self._config_if_changed(self.status_roi_lbl, fg=COLORS["muted"])

        # Bloco 3: modo ativo
        if self.pan_mode:
            self._set_var_if_changed(self.status_mode_var, "● Pan")
            self._config_if_changed(self.status_mode_lbl, fg=COLORS["primary"])
        elif self.annotation_mode:
            self._set_var_if_changed(self.status_mode_var, "● Anotação")
            self._config_if_changed(self.status_mode_lbl, fg=COLORS["accent"])
        elif self.remove_mode:
            self._set_var_if_changed(self.status_mode_var, "● Remoção")
            self._config_if_changed(self.status_mode_lbl, fg=COLORS["danger"])
        elif self.edit_id_mode:
            self._set_var_if_changed(self.status_mode_var, "● Editar ID")
            self._config_if_changed(self.status_mode_lbl, fg=COLORS["accent"])
        elif self.selection_mode:
            self._set_var_if_changed(self.status_mode_var, "● Seleção")
            self._config_if_changed(self.status_mode_lbl, fg=COLORS["primary"])
        else:
            self._set_var_if_changed(self.status_mode_var, "Validação")
            self._config_if_changed(self.status_mode_lbl, fg=COLORS["muted"])

        # Bloco 4: classe ativa + contagem
        active = self.active_class_name() if hasattr(self, "active_class_name") else ""
        n_det = len(self.current_detections) + len(self.manual_detections)
        cat_colors = self.category_color_by_id() if hasattr(self, "category_color_by_id") else {}
        cat_id = self.class_to_category_id.get(active, 0)
        cls_color = cat_colors.get(cat_id, COLORS["muted"])
        self._set_var_if_changed(self.status_class_var, f"● {active}  ·  {n_det} det.")
        self._config_if_changed(self.status_class_lbl, fg=cls_color)

        # Bloco 5: seleção
        sel = self.get_selected_detection() if hasattr(self, "get_selected_detection") else None
        if sel is not None and sel.track_id is not None:
            self._set_var_if_changed(self.status_sel_var, f"ID #{sel.track_id}")
            self._config_if_changed(self.status_sel_lbl, fg=COLORS["text"])
        else:
            self._set_var_if_changed(self.status_sel_var, "")

    def current_display_file_name(self) -> str:
        """Nome amigavel da imagem/frame atual."""
        record = self.current_review_record()
        if record is not None:
            return str(record.get("file_name", "-"))
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            return self.current_source_image_path.name
        return f"{self.video_name}_frame_{self.frame_index:05d}.jpg"

    def current_open_target_path(self) -> Optional[Path]:
        """Retorna caminho da imagem atual que pode ser aberta no gerenciador."""
        record = self.current_review_record()
        if record is not None:
            file_name = record.get("file_name")
            if file_name:
                saved_path = self.output_images_dir / str(file_name)
                if saved_path.exists():
                    return saved_path
            return None
        file_name = self.current_frame_file_name()
        if file_name:
            saved_path = self.output_images_dir / file_name
            if saved_path.exists():
                return saved_path
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            if self.current_source_image_path.exists():
                return self.current_source_image_path
        return None

    def update_image_info(self):
        """Atualiza label do nome da imagem e estado do botao 'Ver em folder'."""
        self._set_var_if_changed(self.image_name_var, f"Imagem: {self.current_display_file_name()}")
        target = self.current_open_target_path()
        self._config_if_changed(self.open_folder_button, state=(tk.NORMAL if target is not None else tk.DISABLED))
        delete_target = self.current_deletable_image_path()
        self._config_if_changed(self.delete_image_button, state=(tk.NORMAL if delete_target is not None else tk.DISABLED))

    def open_in_file_manager(self, target: Path) -> bool:
        """Abre o gerenciador de arquivos e tenta destacar o arquivo alvo."""
        target = target.resolve()
        folder = target.parent

        def _spawn(cmd: List[str]) -> bool:
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:  # pylint: disable=broad-except
                return False

        try:
            if sys.platform.startswith("linux"):
                candidates = []
                for app in ("nautilus", "nemo", "dolphin"):
                    exe = shutil.which(app)
                    if exe:
                        candidates.append([exe, "--select", str(target)])
                thunar = shutil.which("thunar")
                if thunar:
                    candidates.append([thunar, str(target)])
                for cmd in candidates:
                    if _spawn(cmd):
                        return True
                gio = shutil.which("gio")
                if gio and _spawn([gio, "open", str(folder)]):
                    return True
                xdg_open = shutil.which("xdg-open")
                if xdg_open:
                    return _spawn([xdg_open, str(folder)])
                return False
            if sys.platform == "darwin":
                return _spawn(["open", "-R", str(target)])
            if os.name == "nt":
                return _spawn(["explorer", "/select,", str(target)])
        except Exception:  # pylint: disable=broad-except
            return False
        return False

    def on_open_in_folder(self):
        """Evento do botao para abrir a imagem atual no gerenciador de arquivos."""
        target = self.current_open_target_path()
        if target is None and self.current_frame is not None:
            saved = self.autosave_current_frame(reason="abrir no folder")
            if saved is not None:
                _image_id, file_name = saved
                target = self.output_images_dir / file_name
        if target is None:
            print("[INFO] Nenhuma imagem de arquivo disponivel neste frame.")
            return
        if not target.exists():
            print(f"[AVISO] Arquivo nao encontrado: {target}")
            return
        if not self.open_in_file_manager(target):
            print(f"[AVISO] Nao foi possivel abrir o gerenciador para: {target}")
            return
        print(f"[INFO] Abrindo no gerenciador: {target}")
