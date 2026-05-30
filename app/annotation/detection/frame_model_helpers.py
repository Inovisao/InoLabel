from app.annotation.shared import *


class FrameModelHelpersMixin:
    def _extract_model_candidates(
        self, frame: np.ndarray, img_width: int, img_height: int
    ) -> Tuple[List[np.ndarray], List[float], List[int]]:
        models = self.ensure_models_loaded()
        all_dets: List[np.ndarray] = []
        all_scores: List[float] = []
        all_cat_ids: List[int] = []

        for model in models:
            yolo_result = model(frame, verbose=False)[0]
            names = yolo_result.names
            for box in getattr(yolo_result, "boxes", []):
                conf = float(box.conf)
                cls_id = int(box.cls)
                label = self._resolve_class_label(names, cls_id)
                if not self._should_keep_detection(conf, label):
                    continue
                category_id = self._resolve_category_id(label, cls_id)
                if category_id is None:
                    continue
                xyxy = box.xyxy.cpu().numpy()[0]
                xyxy[0::2] = np.clip(xyxy[0::2], 0, img_width - 1)
                xyxy[1::2] = np.clip(xyxy[1::2], 0, img_height - 1)
                all_dets.append(xyxy)
                all_scores.append(conf)
                all_cat_ids.append(category_id)

        if len(models) > 1:
            return self._nms_ensemble(all_dets, all_scores, all_cat_ids)
        return all_dets, all_scores, all_cat_ids

    @staticmethod
    def _nms_ensemble(
        dets: List[np.ndarray],
        scores: List[float],
        category_ids: List[int],
        iou_threshold: float = 0.5,
    ) -> Tuple[List[np.ndarray], List[float], List[int]]:
        """Per-category NMS to remove duplicates from the model ensemble."""
        if not dets:
            return dets, scores, category_ids

        result_dets: List[np.ndarray] = []
        result_scores: List[float] = []
        result_cats: List[int] = []

        for cat in set(category_ids):
            indices = [i for i, c in enumerate(category_ids) if c == cat]
            boxes = [
                [float(dets[i][0]), float(dets[i][1]),
                 float(dets[i][2] - dets[i][0]), float(dets[i][3] - dets[i][1])]
                for i in indices
            ]
            cat_scores = [float(scores[i]) for i in indices]
            kept = cv2.dnn.NMSBoxes(boxes, cat_scores, score_threshold=0.0, nms_threshold=iou_threshold)
            for k in (kept.flatten() if len(kept) > 0 else []):
                result_dets.append(dets[indices[k]])
                result_scores.append(scores[indices[k]])
                result_cats.append(cat)

        return result_dets, result_scores, result_cats

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
        return True

    def _resolve_category_id(self, label: str, cls_id: Optional[int] = None) -> Optional[int]:
        clean_label = str(label).strip()
        if not clean_label:
            return None

        for class_name in self.target_classes:
            if clean_label == class_name:
                return self.register_category(class_name)

        normalized_label = clean_label.casefold()
        for class_name in self.target_classes:
            if normalized_label == class_name.casefold():
                return self.register_category(class_name)

        if cls_id is not None and 0 <= int(cls_id) < len(self.target_classes):
            return self.register_category(self.target_classes[int(cls_id)])

        if not self.target_classes:
            return self.register_category(clean_label)

        print(f"[AVISO] Classe do modelo ignorada por nao existir na UI: {clean_label}")
        return None

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
