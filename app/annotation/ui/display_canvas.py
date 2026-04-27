from app.annotation.shared import *


class DisplayCanvasMixin:
    def image_to_canvas_coords(self, x: float, y: float) -> Tuple[int, int]:
        cx = int(round(x * self.display_scale + self.offset_x))
        cy = int(round(y * self.display_scale + self.offset_y))
        return cx, cy

    def canvas_to_image_coords(self, canvas_x: int, canvas_y: int) -> Optional[Tuple[int, int]]:
        if self.current_frame is None:
            return None
        frame_h, frame_w = self.current_frame.shape[:2]
        x = (canvas_x - self.offset_x) / max(self.display_scale, 1e-9)
        y = (canvas_y - self.offset_y) / max(self.display_scale, 1e-9)
        if x < 0 or y < 0 or x >= frame_w or y >= frame_h:
            return None
        x_i = int(np.clip(x, 0, frame_w - 1))
        y_i = int(np.clip(y, 0, frame_h - 1))
        return x_i, y_i

    def update_display(self):
        if self.current_frame is None:
            return

        annotated = self.current_frame.copy()
        annotated = self._draw_roi_overlay_on_frame(annotated)
        self.validate_selected_detection()

        if SHOW_MODEL_DETECTIONS:
            annotated = self.draw_detections(annotated, self.current_detections, "model")
        if SHOW_MANUAL_DETECTIONS:
            annotated = self.draw_detections(annotated, self.manual_detections, "manual")

        frame_h, frame_w = annotated.shape[:2]
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        max_canvas_w = max(320, screen_w - WINDOW_MARGIN_PX)
        max_canvas_h = max(240, screen_h - WINDOW_TOP_RESERVED_PX)
        disp_w, disp_h = self._compute_display_size(frame_w, frame_h, max_canvas_w, max_canvas_h)
        if self.display_scale < 1.0:
            annotated = cv2.resize(annotated, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
        self._render_frame_on_canvas(annotated, disp_w, disp_h, max_canvas_w, max_canvas_h, screen_w, screen_h)
        self._draw_roi_overlay_on_canvas()
        self._draw_active_manual_rectangle()

        self.last_frame_shape = (frame_w, frame_h)
        self.update_status()

    def _draw_roi_overlay_on_frame(self, frame: np.ndarray) -> np.ndarray:
        if not self.roi_points:
            return frame
        pts = np.array(self.roi_points, dtype=np.int32)
        is_closed = len(self.roi_points) == 4
        cv2.polylines(frame, [pts], isClosed=is_closed, color=(255, 0, 0), thickness=2)
        for idx, (x, y) in enumerate(self.roi_points):
            xi, yi = int(round(x)), int(round(y))
            cv2.circle(frame, (xi, yi), 4, (0, 0, 255), -1)
            cv2.putText(frame, str(idx + 1), (xi + 4, yi - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        return frame

    def _compute_display_size(
        self, frame_w: int, frame_h: int, max_canvas_w: int, max_canvas_h: int
    ) -> Tuple[int, int]:
        self.display_scale = min(1.0, max_canvas_w / frame_w, max_canvas_h / frame_h)
        disp_w = max(1, int(round(frame_w * self.display_scale)))
        disp_h = max(1, int(round(frame_h * self.display_scale)))
        return disp_w, disp_h

    def _render_frame_on_canvas(
        self,
        frame: np.ndarray,
        disp_w: int,
        disp_h: int,
        max_canvas_w: int,
        max_canvas_h: int,
        screen_w: int,
        screen_h: int,
    ):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        self.tk_image = ImageTk.PhotoImage(image=pil_image)

        self.canvas.delete("all")
        canvas_w = min(max_canvas_w, disp_w + CANVAS_PADDING_PX)
        canvas_h = min(max_canvas_h, disp_h + CANVAS_PADDING_PX)
        self.offset_x = (canvas_w - disp_w) // 2
        self.offset_y = (canvas_h - disp_h) // 2
        self.canvas.config(width=canvas_w, height=canvas_h)
        self.canvas_image_id = self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.tk_image)
        self.window.maxsize(screen_w, screen_h)
