"""Composicao da ferramenta OBB — pura, sem dependencias de UI."""

from backend.annotation.state.noop_ui import NoopUIMixin
from backend.annotation.state.core_init import CoreInitMixin
from backend.annotation.core.services.class_service import ClassServiceMixin
from backend.annotation.sources.source_discovery import SourceDiscoveryMixin
from backend.annotation.sources.source_loading import SourceLoadingMixin
from backend.annotation.roi.roi_state import ROIStateMixin
from backend.annotation.roi.roi_projection import ROIProjectionMixin
from backend.annotation.application.lifecycle import LifecycleMixin
from backend.annotation_obb.state.runtime_state import OBBRuntimeStateMixin
from backend.annotation_obb.sources.source_helpers import OBBSourceHelpersMixin
from backend.annotation_obb.detection.frame_pipeline import OBBFramePipelineMixin
from backend.annotation_obb.detection.frame_model_helpers import OBBFrameModelHelpersMixin
from backend.annotation_obb.detection.workflow_actions import OBBWorkflowActionsMixin
from backend.annotation_obb.detection.review_nav import OBBReviewNavMixin
from backend.annotation_obb.detection.selection_edit import OBBSelectionEditMixin
from backend.annotation_obb.infrastructure.persistence.obb_coco_storage import OBBCocoStorageMixin
from backend.annotation_obb.infrastructure.persistence.export_actions import OBBExportActionsMixin
from backend.annotation_obb.ui.display_overlays import OBBDisplayOverlaysMixin
from backend.annotation_obb.ui.display_status import OBBDisplayStatusMixin
from backend.annotation.ui.rotation_utils import apply_frame_rotation


class OBBAnnotationTool(
    NoopUIMixin,
    CoreInitMixin,
    OBBRuntimeStateMixin,
    ClassServiceMixin,
    SourceDiscoveryMixin,
    OBBCocoStorageMixin,
    SourceLoadingMixin,
    OBBSourceHelpersMixin,
    ROIStateMixin,
    ROIProjectionMixin,
    OBBFramePipelineMixin,
    OBBFrameModelHelpersMixin,
    OBBWorkflowActionsMixin,
    OBBReviewNavMixin,
    OBBSelectionEditMixin,
    OBBExportActionsMixin,
    LifecycleMixin,
    OBBDisplayOverlaysMixin,
    OBBDisplayStatusMixin,
):
    """Ferramenta de anotacao OBB pura — sem UI."""

    def __init__(self, **kwargs):
        self._init_noop_vars()
        super().__init__(**kwargs)

    def render_frame(self) -> bytes:
        """Renderiza frame atual com overlays OBB e retorna como JPEG bytes."""
        from io import BytesIO
        import cv2
        from PIL import Image

        if self.current_frame is None:
            return b""

        frame = self.current_frame.copy()
        frame = self.draw_roi_overlay_on_frame(frame)
        frame = self.draw_obb_detections(frame, self.current_obb_detections, "model")
        frame = self.draw_obb_detections(frame, self.manual_obb_detections, "manual")

        rotation = getattr(self, "frame_rotation", 0)
        if rotation:
            frame = apply_frame_rotation(frame, rotation)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        buf = BytesIO()
        pil_img.save(buf, format="JPEG", quality=88, optimize=True)
        return buf.getvalue()

    def get_state_snapshot(self) -> dict:
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
            "pan_mode": self.pan_mode,
            "roi_defined": self.roi_defined,
            "roi_points": list(self.roi_points),
            "status_message": self.build_status_message(),
            "classes": self.target_classes,
            "categories": self.categories,
            "current_obb_detections": self._serialize_obb_detections(self.current_obb_detections),
            "manual_obb_detections": self._serialize_obb_detections(self.manual_obb_detections),
            "info": self.info_var.get(),
        }

    @staticmethod
    def _serialize_obb_detections(detections) -> list:
        return [
            {
                "cx": float(det.cx),
                "cy": float(det.cy),
                "width": float(det.width),
                "height": float(det.height),
                "angle": float(det.angle),
                "confidence": float(det.confidence),
                "category_id": det.category_id,
                "source": det.source,
            }
            for det in detections
        ]
