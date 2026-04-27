from app.annotation.shared import *


class DisplayStatusMixin:
    def build_status_message(self) -> str:
        """Gera mensagem de status para a barra de informacoes."""
        base = (
            f"[{self.current_video_index + 1}/{len(self.video_files)}] {self.video_name} | "
            f"Frame {self.frame_index} | Deteccoes validas (> {CONF_THRESHOLD*100:.0f}%): "
            f"{len(self.current_detections)}"
        )
        if self.review_idx is not None and self.saved_records:
            base = (
                f"[Revisao {self.review_idx + 1}/{len(self.saved_records)}] "
                f"{self.video_name} | Frame {self.frame_index} | Deteccoes: {len(self.current_detections)}"
            )
        if self.last_frame_shape:
            width, height = self.last_frame_shape
            base += f" | Resolucao: {width}x{height}"
        if self.roi_defined and self.warp_size:
            base += f" | ROI retificado: {self.warp_size[0]}x{self.warp_size[1]}"
        else:
            base += f" | ROI: {len(self.roi_points)}/4 pontos"
        base += f" | Modo anotacao: {'ON' if self.annotation_mode else 'OFF'}"
        base += f" | Remover anotacao: {'ON' if self.remove_mode else 'OFF'}"
        base += f" | Editar ID: {'ON' if self.edit_id_mode else 'OFF'}"
        selected = self.get_selected_detection()
        if selected is not None:
            base += f" | Selecionada ID {selected.track_id}"
        if self.manual_detections:
            base += f" | BBoxes manuais: {len(self.manual_detections)}"
        if self.target_classes:
            base += f" | Classes alvo: {', '.join(self.target_classes)}"
        if self.manual_class_var is not None and self.manual_class_var.get().strip():
            base += f" | Classe manual: {self.manual_class_var.get().strip()}"
        base += f" | Salvando frames {'retificados' if SAVE_RECTIFIED_FRAMES else 'originais'}"
        return base

    def update_status(self):
        """Atualiza o texto de status exibido na interface."""
        self.info_var.set(self.build_status_message())
        self.update_image_info()
        self.update_annotation_button()
        self.update_remove_button()
        self.update_edit_id_button()

    def current_display_file_name(self) -> str:
        """Nome amigavel da imagem/frame atual."""
        if self.review_idx is not None and self.saved_records:
            return str(self.saved_records[self.review_idx].get("file_name", "-"))
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            return self.current_source_image_path.name
        return f"{self.video_name}_frame_{self.frame_index:05d}.jpg"

    def current_open_target_path(self) -> Optional[Path]:
        """Retorna caminho da imagem atual que pode ser aberta no gerenciador."""
        if self.review_idx is not None and self.saved_records:
            file_name = self.saved_records[self.review_idx].get("file_name")
            if file_name:
                saved_path = OUTPUT_IMAGES_DIR / str(file_name)
                if saved_path.exists():
                    return saved_path
            return None
        if self.current_source_type == "images" and self.current_source_image_path is not None:
            if self.current_source_image_path.exists():
                return self.current_source_image_path
        return None

    def update_image_info(self):
        """Atualiza label do nome da imagem e estado do botao 'Ver em folder'."""
        self.image_name_var.set(f"Imagem: {self.current_display_file_name()}")
        target = self.current_open_target_path()
        self.open_folder_button.config(state=(tk.NORMAL if target is not None else tk.DISABLED))

    def open_in_file_manager(self, target: Path) -> bool:
        """Abre o gerenciador de arquivos e tenta destacar o arquivo alvo."""
        target = target.resolve()
        folder = target.parent
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "check": False}
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
                    if subprocess.run(cmd, **kwargs).returncode == 0:
                        return True
                xdg_open = shutil.which("xdg-open")
                if xdg_open:
                    return subprocess.run([xdg_open, str(folder)], **kwargs).returncode == 0
                return False
            if sys.platform == "darwin":
                return subprocess.run(["open", "-R", str(target)], **kwargs).returncode == 0
            if os.name == "nt":
                return subprocess.run(["explorer", "/select,", str(target)], **kwargs).returncode == 0
        except Exception:  # pylint: disable=broad-except
            return False
        return False

    def on_open_in_folder(self):
        """Evento do botao para abrir a imagem atual no gerenciador de arquivos."""
        target = self.current_open_target_path()
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

