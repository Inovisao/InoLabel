from app.annotation.shared import *


class UILayoutMixin:
    def _build_ui(self):
        self.window = tk.Tk()
        self.window.title("Validador de deteccoes")
        self.window.protocol("WM_DELETE_WINDOW", self.on_quit)

        self._initialize_ui_variables()
        self._build_info_bar()
        self._build_image_header()
        self._build_action_controls()
        self._bind_shortcuts()
        self._build_canvas()

    def _initialize_ui_variables(self):
        self.manual_id_var = tk.StringVar(value="")
        self.manual_class_var = tk.StringVar(value=(self.target_classes[0] if self.target_classes else "car"))
        self.target_classes_var = tk.StringVar(value=", ".join(self.target_classes))
        self.image_name_var = tk.StringVar(value="Imagem: -")
        self.info_var = tk.StringVar(value="ROI opcional. Pressione R para definir 4 pontos.")

    def _build_info_bar(self):
        self.info_label = tk.Label(self.window, textvariable=self.info_var, font=("Arial", 12))
        self.info_label.pack(pady=10)

    def _build_image_header(self):
        self.image_row = tk.Frame(self.window)
        self.image_row.pack(pady=(0, 6))
        self.image_name_label = tk.Label(self.image_row, textvariable=self.image_name_var, font=("Arial", 11))
        self.image_name_label.pack(side=tk.LEFT, padx=(0, 8))
        self.open_folder_button = tk.Button(
            self.image_row,
            text="Ver em folder",
            command=self.on_open_in_folder,
            width=16,
            state=tk.DISABLED,
        )
        self.open_folder_button.pack(side=tk.LEFT)

    def _build_action_controls(self):
        self.buttons_frame = tk.Frame(self.window)
        self.buttons_frame.pack(pady=10)

        self.accept_button = tk.Button(
            self.buttons_frame, text="Validar (Enter)", command=self.on_accept, width=18, state=tk.DISABLED
        )
        self.accept_button.grid(row=0, column=0, padx=5)
        self.reject_button = tk.Button(
            self.buttons_frame, text="Rejeitar (Espaco)", command=self.on_reject, width=18, state=tk.DISABLED
        )
        self.reject_button.grid(row=0, column=1, padx=5)
        self.quit_button = tk.Button(self.buttons_frame, text="Sair (Esc)", command=self.on_quit, width=18)
        self.quit_button.grid(row=0, column=2, padx=5)
        self.annotation_button = tk.Button(
            self.buttons_frame,
            text="Modo anotacao ON (K)",
            command=self.toggle_annotation_mode,
            width=22,
            state=tk.DISABLED,
        )
        self.annotation_button.grid(row=0, column=3, padx=5)
        self.remove_button = tk.Button(
            self.buttons_frame,
            text="Remover anotacao OFF",
            command=self.toggle_remove_mode,
            width=22,
            state=tk.DISABLED,
        )
        self.remove_button.grid(row=0, column=4, padx=5)
        self.roi_button = tk.Button(
            self.buttons_frame,
            text="Redefinir ROI (R)",
            command=self.reset_roi,
            width=18,
        )
        self.roi_button.grid(row=0, column=5, padx=5)

        self.prev_button = tk.Button(self.buttons_frame, text="< Frame anterior", command=self.on_prev_saved, width=18)
        self.prev_button.grid(row=1, column=0, padx=5, pady=(6, 0))
        self.next_button = tk.Button(self.buttons_frame, text="Proximo frame >", command=self.on_next_saved, width=18)
        self.next_button.grid(row=1, column=1, padx=5, pady=(6, 0))
        self.manual_id_label = tk.Label(self.buttons_frame, text="ID manual:")
        self.manual_id_label.grid(row=1, column=2, padx=5, pady=(6, 0))
        self.manual_id_entry = tk.Entry(self.buttons_frame, textvariable=self.manual_id_var, width=10)
        self.manual_id_entry.grid(row=1, column=3, padx=5, pady=(6, 0))
        self.apply_id_button = tk.Button(
            self.buttons_frame, text="Aplicar ID", command=self.apply_manual_id_to_selection, width=12, state=tk.DISABLED
        )
        self.apply_id_button.grid(row=1, column=4, padx=5, pady=(6, 0))
        self.edit_id_button = tk.Button(
            self.buttons_frame, text="Editar ID OFF (E)", command=self.toggle_edit_id_mode, width=16, state=tk.DISABLED
        )
        self.edit_id_button.grid(row=1, column=5, padx=5, pady=(6, 0))

        self.classes_label = tk.Label(self.buttons_frame, text="Classes (csv):")
        self.classes_label.grid(row=2, column=0, padx=5, pady=(6, 0))
        self.classes_entry = tk.Entry(self.buttons_frame, textvariable=self.target_classes_var, width=28)
        self.classes_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=(6, 0), sticky="we")
        self.apply_classes_button = tk.Button(
            self.buttons_frame, text="Aplicar classes", command=self.apply_target_classes_from_ui, width=16
        )
        self.apply_classes_button.grid(row=2, column=3, padx=5, pady=(6, 0))
        self.manual_class_label = tk.Label(self.buttons_frame, text="Classe manual:")
        self.manual_class_label.grid(row=2, column=4, padx=5, pady=(6, 0))
        self.manual_class_entry = tk.Entry(self.buttons_frame, textvariable=self.manual_class_var, width=14)
        self.manual_class_entry.grid(row=2, column=5, padx=5, pady=(6, 0))

        self.save_yaml_button = tk.Button(
            self.buttons_frame,
            text="Salvar .yaml",
            command=self.on_save_yaml,
            width=18,
            state=tk.DISABLED,
        )
        self.save_yaml_button.grid(row=3, column=0, padx=5, pady=(6, 0))
        self.save_coco_button = tk.Button(
            self.buttons_frame,
            text="Salvar .coco.json",
            command=self.on_save_coco_json,
            width=18,
            state=tk.DISABLED,
        )
        self.save_coco_button.grid(row=3, column=1, padx=5, pady=(6, 0))
