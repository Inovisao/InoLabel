from app.annotation.shared import *


class ROIProjectionMixin:
    def warp_frame(self, frame: np.ndarray) -> np.ndarray:
        """Aplica warpPerspective ao frame atual usando a homografia."""
        if self.homography_matrix is None or self.warp_size is None:
            return frame
        try:
            return cv2.warpPerspective(frame, self.homography_matrix, self.warp_size)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[AVISO] Falha ao aplicar ROI; usando frame original: {exc}")
            self.homography_matrix = None
            self.inverse_homography = None
            self.warp_size = None
            self.roi_polygon = None
            self.dest_points = None
            self.roi_defined = False
            return frame

    def project_bbox(
        self, bbox: np.ndarray, matrix: Optional[np.ndarray], width: int, height: int
    ) -> np.ndarray:
        """Projeta bbox xyxy usando a matriz de homografia fornecida."""
        if matrix is None:
            return bbox.astype(np.float32)
        pts = np.array(
            [
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
            ],
            dtype=np.float32,
        ).reshape((1, 4, 2))
        projected = cv2.perspectiveTransform(pts, matrix)[0]
        xs = projected[:, 0]
        ys = projected[:, 1]
        return clip_bbox(xs.min(), ys.min(), xs.max(), ys.max(), width, height)

    def is_inside_roi(self, bbox: np.ndarray) -> bool:
        """Verifica se a bbox está majoritariamente dentro do ROI."""
        if self.roi_polygon is None:
            return True
        if len(self.roi_polygon) < 3:
            return True

        x1, y1, x2, y2 = bbox
        box_pts = np.array(
            [
                [x1, y1],
                [x2, y1],
                [x2, y2],
                [x1, y2],
            ],
            dtype=np.float32,
        )
        poly = self.roi_polygon.astype(np.float32)
        if cv2.contourArea(poly) <= 1:
            return True

        inside_count = 0
        for (px, py) in box_pts:
            if cv2.pointPolygonTest(poly, (px, py), False) >= 0:
                inside_count += 1
        return inside_count >= 3
