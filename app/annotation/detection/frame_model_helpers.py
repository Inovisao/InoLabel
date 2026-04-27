from app.annotation.shared import *


class FrameModelHelpersMixin:
    def _extract_model_candidates(
        self, frame: np.ndarray, img_width: int, img_height: int
    ) -> Tuple[List[np.ndarray], List[float], List[int]]:
        model = self.ensure_model_loaded()
        yolo_result = model(frame, verbose=False)[0]
        names = yolo_result.names

        dets: List[np.ndarray] = []
        scores: List[float] = []
        det_category_ids: List[int] = []
        for box in getattr(yolo_result, "boxes", []):
            conf = float(box.conf)
            cls_id = int(box.cls)
            label = self._resolve_class_label(names, cls_id)
            if not self._should_keep_detection(conf, label):
                continue
            category_id = self._resolve_category_id(label)
            xyxy = box.xyxy.cpu().numpy()[0]
            xyxy[0::2] = np.clip(xyxy[0::2], 0, img_width - 1)
            xyxy[1::2] = np.clip(xyxy[1::2], 0, img_height - 1)
            dets.append(xyxy)
            scores.append(conf)
            det_category_ids.append(category_id)
        return dets, scores, det_category_ids

    @staticmethod
    def _resolve_class_label(names, cls_id: int) -> str:
        if isinstance(names, dict):
            return str(names.get(cls_id, str(cls_id)))
        if isinstance(names, list):
            return str(names[cls_id]) if 0 <= cls_id < len(names) else str(cls_id)
        return str(cls_id)

    def _should_keep_detection(self, conf: float, label: str) -> bool:
        if conf < self.conf_threshold:
            return False
        if not self.uses_text_prompt and self.target_classes and label not in self.class_to_category_id:
            return False
        return True

    def _resolve_category_id(self, label: str) -> int:
        category_id = self.class_to_category_id.get(label)
        if category_id is not None:
            return category_id
        if self.uses_text_prompt and len(self.target_classes) == 1:
            return self.register_category(self.target_classes[0])
        return self.register_category(label)

    @staticmethod
    def _match_track_category(original_box: np.ndarray, dets: List[np.ndarray], det_category_ids: List[int]) -> int:
        if not dets or not det_category_ids:
            return 1
        best_iou = 0.0
        best_category = det_category_ids[0]
        for det_box, det_cid in zip(dets, det_category_ids):
            iou = bbox_iou(original_box, np.array(det_box, dtype=np.float32))
            if iou > best_iou:
                best_iou = iou
                best_category = det_cid
        return best_category
