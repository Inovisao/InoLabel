from app.annotation.shared import *


class ReviewAnnotationsMixin:
    def rebuild_detections_from_annotations(self, image_id: int, width: int, height: int) -> List[Detection]:
        """Rebuilds Detection objects from saved COCO annotations for a given image."""
        dets: List[Detection] = []
        for ann in self.annotations:
            if ann.get("image_id") != image_id:
                continue
            x1, y1, w, h = ann.get("bbox", [0, 0, 0, 0])
            clipped = clip_bbox(x1, y1, x1 + w, y1 + h, width, height)
            dets.append(Detection(
                original_bbox=clipped,
                warp_bbox=None,
                confidence=float(ann.get("score", 1.0)),
                category_id=int(ann.get("category_id", 1)),
                track_id=(int(ann["track_id"]) if ann.get("track_id") is not None else None),
                source=ann.get("source", "manual"),
                internal_id=None,
            ))
        return dets

    def restore_saved_annotations_for_current_frame(self):
        """Restores annotations for the current frame if it was already saved."""
        file_name = self.current_frame_file_name()
        if not file_name:
            return
        record = self.find_image_record_by_file_name(file_name)
        if record is None or self.current_frame is None:
            return
        dets = self.rebuild_detections_from_annotations(
            int(record["id"]),
            self.current_frame.shape[1],
            self.current_frame.shape[0],
        )
        self.current_detections = [d for d in dets if d.source == "model"]
        self.manual_detections = [d for d in dets if d.source != "model"]
        self.selected_detection = None
