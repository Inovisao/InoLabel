from app.annotation_obb.shared import *


class OBBFrameModelHelpersMixin:
    def _extract_model_obb_candidates(self, frame: np.ndarray, img_width: int, img_height: int) -> List[OBBDetection]:
        models = self.ensure_models_loaded()
        detections: List[OBBDetection] = []
        for model in models:
            yolo_result = model(frame, verbose=False)[0]
            names = yolo_result.names
            for box in getattr(yolo_result, "boxes", []):
                conf = float(box.conf)
                cls_id = int(box.cls)
                label = self._resolve_class_label(names, cls_id)
                if conf < self.conf_threshold:
                    continue
                category_id = self._resolve_category_id(label, cls_id)
                if category_id is None:
                    continue
                xyxy = box.xyxy.cpu().numpy()[0]
                xyxy[0::2] = np.clip(xyxy[0::2], 0, img_width - 1)
                xyxy[1::2] = np.clip(xyxy[1::2], 0, img_height - 1)
                x1, y1, x2, y2 = xyxy
                obb = hbb_to_obb(
                    x1,
                    y1,
                    x2 - x1,
                    y2 - y1,
                    category_id=category_id,
                    confidence=conf,
                    source="model",
                )
                detections.append(obb)
        return detections

    @staticmethod
    def _resolve_class_label(names, cls_id: int) -> str:
        if isinstance(names, dict):
            return str(names.get(cls_id, str(cls_id)))
        if isinstance(names, list):
            return str(names[cls_id]) if 0 <= cls_id < len(names) else str(cls_id)
        return str(cls_id)

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
        if clean_label not in self.target_classes:
            self.target_classes.append(clean_label)
            if getattr(self, "target_classes_var", None) is not None:
                self.target_classes_var.set(", ".join(self.target_classes))
            self._class_panel_snapshot = None
        return self.register_category(clean_label)
