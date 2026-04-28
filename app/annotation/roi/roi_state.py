from app.annotation.shared import *


class ROIStateMixin:
    def reset_roi(self):
        """Ativa/desativa captura de ROI e redefine a homografia atual."""
        if self.frames_saved_in_current_video > 0:
            print(
                "[AVISO] ROI redefinido mesmo com frames salvos; anotacoes ja salvas nao serao alteradas."
            )
        if self.roi_capture_mode:
            self.roi_capture_mode = False
            self.roi_points = []
            self.roi_defined = False
            self.homography_matrix = None
            self.inverse_homography = None
            self.warp_size = None
            self.roi_polygon = None
            self.dest_points = None
            if self.current_frame is not None:
                self.process_current_frame(self.current_frame, advance_index=False)
            print("[INFO] Captura de ROI cancelada. Seguira sem ROI.")
            return

        self.roi_capture_mode = True
        self.roi_points = []
        self.roi_defined = False
        self.homography_matrix = None
        self.inverse_homography = None
        self.warp_size = None
        self.roi_polygon = None
        self.dest_points = None
        self.current_rectified_frame = None
        self.current_detections = []
        self.manual_detections = []
        self.edit_id_mode = False
        self.selected_detection = None
        self.enable_controls_after_roi()
        self.info_var.set("Selecione 4 pontos do ROI (ou pressione R novamente para cancelar).")
        self.update_display(refresh_status=True)

    def add_roi_point(self, x: int, y: int):
        """Registra ponto clicado para ROI."""
        if len(self.roi_points) >= 4:
            return
        if self.current_frame is not None:
            frame_h, frame_w = self.current_frame.shape[:2]
            x = int(np.clip(x, 0, frame_w - 1))
            y = int(np.clip(y, 0, frame_h - 1))
        for px, py in self.roi_points:
            if abs(px - x) < 3 and abs(py - y) < 3:
                print("[AVISO] Ponto de ROI muito proximo de outro ponto; escolha outro local.")
                return
        self.roi_points.append((float(x), float(y)))
        if len(self.roi_points) == 4:
            self.compute_homography()
        self.update_display(refresh_status=True)

    def compute_homography(self):
        """Calcula homografia a partir dos 4 pontos clicados."""
        if len(self.roi_points) != 4:
            return
        src = order_points(np.array(self.roi_points, dtype=np.float32))
        width, height = destination_size(src)
        area = cv2.contourArea(src.astype(np.float32))
        if width < 5 or height < 5 or area < 25:
            print("[ERRO] ROI invalida. Selecione 4 pontos formando uma area maior.")
            self.roi_points = []
            self.roi_defined = False
            self.roi_capture_mode = True
            self.homography_matrix = None
            self.inverse_homography = None
            self.warp_size = None
            self.roi_polygon = None
            self.dest_points = None
            self.update_display(refresh_status=True)
            return
        dst = np.array(
            [
                [0, 0],
                [width - 1, 0],
                [width - 1, height - 1],
                [0, height - 1],
            ],
            dtype=np.float32,
        )
        try:
            self.homography_matrix = cv2.getPerspectiveTransform(src, dst)
            self.inverse_homography = cv2.getPerspectiveTransform(dst, src)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[ERRO] Falha ao calcular ROI: {exc}")
            self.roi_points = []
            self.roi_capture_mode = True
            self.roi_defined = False
            self.homography_matrix = None
            self.inverse_homography = None
            return
        self.warp_size = (width, height)
        self.roi_polygon = src
        self.dest_points = dst
        self.roi_defined = True
        self.roi_capture_mode = False
        self.enable_controls_after_roi()
        self.save_homography_file()
        print(f"[INFO] ROI definida com tamanho retificado {width}x{height}.")
        if self.current_frame is not None:
            self.process_current_frame(self.current_frame, advance_index=False)

    def save_homography_file(self):
        """Persiste homografia em disco (lista para multiplos videos)."""
        if self.homography_matrix is None or self.inverse_homography is None or self.dest_points is None:
            return
        if self.video_path is None:
            return
        payload = {
            "video": str(self.video_path),
            "video_name": self.video_name,
            "roi_points": [[int(x), int(y)] for (x, y) in self.roi_points],
            "ordered_roi": self.roi_polygon.tolist() if self.roi_polygon is not None else None,
            "destination_points": self.dest_points.tolist(),
            "warp_size": {"width": self.warp_size[0], "height": self.warp_size[1]} if self.warp_size else None,
            "homography": self.homography_matrix.tolist(),
            "inverse_homography": self.inverse_homography.tolist(),
        }
        self.homographies = [h for h in self.homographies if h.get("video") != str(self.video_path)]
        self.homographies.append(payload)
        with open(self.homography_path, "w", encoding="utf-8") as f:
            json.dump(self.homographies, f, indent=4, ensure_ascii=False)
        print(f"[INFO] Homografia salva/atualizada em {self.homography_path}")
