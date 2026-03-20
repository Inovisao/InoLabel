from app.annotation.shared import *
from app.dataset_export import export_detection_coco_json, export_yolo_dataset


class PersistenceMixin:
    def build_coco_payload(self) -> dict:
        """Monta o payload COCO/MOT atual em memoria."""
        return {
            "info": {
                "description": "Validacao manual de deteccoes com ROI e homografia",
                "version": "1.0",
                "video_sources": [str(v) for v in self.video_files],
                "frames_are_rectified": SAVE_RECTIFIED_FRAMES,
            },
            "licenses": [],
            "categories": self.categories,
            "images": self.images,
            "annotations": self.annotations,
        }

    def store_annotations(
        self, detections: List[Detection], existing_image_id: Optional[int] = None, existing_file_name: Optional[str] = None
    ) -> Tuple[int, str]:
        """Adiciona as detecoes aprovadas na estrutura COCO MOT e retorna (image_id, file_name)."""
        frame_to_save = (
            self.current_rectified_frame
            if SAVE_RECTIFIED_FRAMES and self.current_rectified_frame is not None
            else self.current_frame
        )
        if frame_to_save is None:
            raise RuntimeError("Frame atual ausente para salvamento.")

        height, width = frame_to_save.shape[:2]
        new_frame = existing_image_id is None
        image_id = self.image_id if new_frame else existing_image_id
        file_name = (
            f"{self.video_name}_frame_{self.frame_index:05d}.jpg" if new_frame or existing_file_name is None else existing_file_name
        )
        image_path = OUTPUT_IMAGES_DIR / file_name
        if not cv2.imwrite(str(image_path), frame_to_save):
            raise RuntimeError(f"Falha ao salvar frame em {image_path}")

        self.images = [img for img in self.images if img.get("id") != image_id]
        image_info = {
            "id": image_id,
            "file_name": file_name,
            "width": width,
            "height": height,
            "video": str(self.video_path) if self.video_path else self.video_name,
        }
        self.images.append(image_info)

        self.annotations = [ann for ann in self.annotations if ann.get("image_id") != image_id]
        for det in detections:
            chosen_bbox = det.warp_bbox if SAVE_RECTIFIED_FRAMES and det.warp_bbox is not None else det.original_bbox
            chosen_bbox = chosen_bbox.astype(np.float32)
            chosen_bbox = clip_bbox(chosen_bbox[0], chosen_bbox[1], chosen_bbox[2], chosen_bbox[3], width, height)
            x1, y1, x2, y2 = chosen_bbox
            w = x2 - x1
            h = y2 - y1
            annotation = {
                "id": self.annotation_id,
                "image_id": image_id,
                "category_id": det.category_id,
                "bbox": [float(x1), float(y1), float(w), float(h)],
                "area": float(max(w, 0.0) * max(h, 0.0)),
                "iscrowd": 0,
                "segmentation": [],
                "score": float(det.confidence),
                "track_id": int(det.track_id),
                "source": det.source,
                "video": str(self.video_path) if self.video_path else self.video_name,
            }
            self.annotations.append(annotation)
            self.annotation_id += 1

        if new_frame:
            self.image_id += 1
            self.frames_saved_in_current_video += 1
        return image_id, file_name

    def write_annotations(self):
        """Grava o arquivo annotations.coco.json com as anotacoes atuais."""
        data = self.build_coco_payload()
        with open(ANNOTATIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[INFO] Anotacoes atualizadas em {ANNOTATIONS_PATH}")

    def on_save_coco_json(self):
        """Exporta as anotacoes atuais para COCO de deteccao."""
        if not self.images:
            self.info_var.set("Nenhuma imagem salva para exportar em .coco.json.")
            return
        try:
            self.write_annotations()
            converted = export_detection_coco_json(self.build_coco_payload(), COCO_DETECTION_EXPORT_PATH)
            message = (
                f"COCO salvo em {COCO_DETECTION_EXPORT_PATH} | "
                f"imagens={len(converted['images'])} anotacoes={len(converted['annotations'])}"
            )
            self.info_var.set(message)
            print(f"[INFO] {message}")
        except Exception as exc:  # pylint: disable=broad-except
            message = f"Falha ao exportar .coco.json: {exc}"
            self.info_var.set(message)
            print(f"[ERRO] {message}")

    def on_save_yaml(self):
        """Exporta as anotacoes atuais para dataset YOLO com data.yaml."""
        if not self.images:
            self.info_var.set("Nenhuma imagem salva para exportar em .yaml.")
            return
        try:
            self.write_annotations()
            report = export_yolo_dataset(
                self.build_coco_payload(),
                source_images_dir=OUTPUT_IMAGES_DIR,
                dataset_root=YOLO_DATASET_DIR,
            )
            message = (
                f"YOLO salvo em {report['dataset_root']} | "
                f"data.yaml={report['data_yaml']} | splits={report['images_per_split']}"
            )
            self.info_var.set(message)
            print(f"[INFO] {message}")
            if report["images_without_annotation"]:
                print(
                    "[AVISO] Imagens sem anotacao: "
                    f"{len(report['images_without_annotation'])} -> {report['images_without_annotation'][:10]}"
                )
            if report["malformed_labels"]:
                print(
                    "[AVISO] Labels mal formatados ignorados: "
                    f"{len(report['malformed_labels'])} -> {report['malformed_labels'][:10]}"
                )
        except Exception as exc:  # pylint: disable=broad-except
            message = f"Falha ao exportar .yaml: {exc}"
            self.info_var.set(message)
            print(f"[ERRO] {message}")

    def finish_processing(self, message: str):
        """Libera recursos e encerra a interface."""
        if self.closed:
            return
        self.closed = True
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.window.unbind("<Return>")
        self.window.unbind("<space>")
        self.window.unbind("<Escape>")
        self.accept_button.config(state=tk.DISABLED)
        self.reject_button.config(state=tk.DISABLED)
        self.quit_button.config(state=tk.DISABLED)
        self.save_yaml_button.config(state=tk.DISABLED)
        self.save_coco_button.config(state=tk.DISABLED)
        if self.images or self.annotations:
            self.write_annotations()
        if self.homographies:
            with open(HOMOGRAPHY_PATH, "w", encoding="utf-8") as f:
                json.dump(self.homographies, f, indent=4, ensure_ascii=False)
        self.info_var.set(message)
        try:
            self.window.after(500, self.window.destroy)
        except Exception:  # pylint: disable=broad-except
            try:
                self.window.destroy()
            except Exception:
                pass

    def run(self):
        """Inicia o loop principal da interface Tkinter."""
        self.window.mainloop()
