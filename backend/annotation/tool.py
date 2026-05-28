"""Composicao da ferramenta de anotacao — pura, sem dependencias de UI."""

from backend.annotation.state.noop_ui import NoopUIMixin
from backend.annotation.state.core_init import CoreInitMixin
from backend.annotation.state.runtime_state import RuntimeStateMixin
from backend.annotation.core.services.class_service import ClassServiceMixin
from backend.annotation.sources.source_discovery import SourceDiscoveryMixin
from backend.annotation.sources.source_loading import SourceLoadingMixin
from backend.annotation.sources.source_helpers import SourceHelpersMixin
from backend.annotation.roi.roi_state import ROIStateMixin
from backend.annotation.roi.roi_projection import ROIProjectionMixin
from backend.annotation.detection.frame_pipeline import FramePipelineMixin
from backend.annotation.detection.frame_model_helpers import FrameModelHelpersMixin
from backend.annotation.detection.tracking_ids import TrackingIdsMixin
from backend.annotation.detection.workflow_actions import WorkflowActionsMixin
from backend.annotation.detection.review_nav import ReviewNavMixin
from backend.annotation.detection.selection_edit import SelectionEditMixin
from backend.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from backend.annotation.infrastructure.persistence.export_actions import ExportActionsMixin
from backend.annotation.application.lifecycle import LifecycleMixin
from backend.annotation.ui.display_overlays import DisplayOverlaysMixin
from backend.annotation.ui.display_status import DisplayStatusMixin
from backend.annotation.ui.rotation_utils import apply_frame_rotation


class AnnotationTool(
    # NoopUIMixin PRIMEIRO — intercepta update_display, info_var, etc.
    NoopUIMixin,
    CoreInitMixin,
    RuntimeStateMixin,
    ClassServiceMixin,
    SourceDiscoveryMixin,
    SourceLoadingMixin,
    SourceHelpersMixin,
    ROIStateMixin,
    ROIProjectionMixin,
    FramePipelineMixin,
    FrameModelHelpersMixin,
    TrackingIdsMixin,
    WorkflowActionsMixin,
    ReviewNavMixin,
    SelectionEditMixin,
    CocoStorageMixin,
    ExportActionsMixin,
    LifecycleMixin,
    DisplayOverlaysMixin,
    DisplayStatusMixin,
):
    """
    Ferramenta de anotacao pura — sem UI.
    Usada pelo servidor FastAPI para expor logica via REST/WebSocket.
    """

    def __init__(self, **kwargs):
        self._init_noop_vars()
        super().__init__(**kwargs)

    def render_frame(self) -> bytes:
        """Renderiza frame atual com overlays e retorna como JPEG bytes."""
        from io import BytesIO
        import cv2
        from PIL import Image
        from backend.config import SHOW_MODEL_DETECTIONS, SHOW_MANUAL_DETECTIONS

        if self.current_frame is None:
            return b""

        frame = self.current_frame.copy()
        frame = self.draw_roi_overlay_on_frame(frame)

        if SHOW_MODEL_DETECTIONS:
            frame = self.draw_detections(frame, self.current_detections, "model")
        if SHOW_MANUAL_DETECTIONS:
            frame = self.draw_detections(frame, self.manual_detections, "manual")

        rotation = getattr(self, "frame_rotation", 0)
        if rotation:
            frame = apply_frame_rotation(frame, rotation)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        buf = BytesIO()
        pil_img.save(buf, format="JPEG", quality=88, optimize=True)
        return buf.getvalue()

    def get_state_snapshot(self) -> dict:
        """Retorna snapshot do estado atual para o frontend."""
        return {
            "mode": self.task_mode.value,
            "frame_index": self.frame_index,
            "video_name": self.video_name,
            "total_sources": len(self.video_files),
            "current_source_index": self.current_video_index,
            "in_review": self.review_idx is not None,
            "review_idx": self.review_idx,
            "total_saved": len(self.saved_records),
            "annotation_mode": self.annotation_mode,
            "remove_mode": self.remove_mode,
            "selection_mode": self.selection_mode,
            "pan_mode": self.pan_mode,
            "edit_id_mode": self.edit_id_mode,
            "zoom_scale": self.zoom_scale,
            "roi_defined": self.roi_defined,
            "roi_points": list(self.roi_points),
            "status_message": self.build_status_message(),
            "classes": self.target_classes,
            "categories": self.categories,
            "current_detections": self._serialize_detections(self.current_detections),
            "manual_detections": self._serialize_detections(self.manual_detections),
            "selected_detection": self.selected_detection,
            "info": self.info_var.get(),
        }

    @staticmethod
    def _serialize_detections(detections) -> list:
        return [
            {
                "bbox": det.original_bbox.tolist(),
                "confidence": float(det.confidence),
                "category_id": det.category_id,
                "track_id": det.track_id,
                "source": det.source,
                "internal_id": det.internal_id,
            }
            for det in detections
        ]
