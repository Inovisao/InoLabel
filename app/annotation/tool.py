"""Composicao da ferramenta principal de anotacao."""

from app.annotation.core_init import CoreInitMixin
from app.annotation.runtime_state import RuntimeStateMixin
from app.annotation.ui_layout import UILayoutMixin
from app.annotation.ui_controls import UIControlsMixin
from app.annotation.source_discovery import SourceDiscoveryMixin
from app.annotation.class_config import ClassConfigMixin
from app.annotation.source_loading import SourceLoadingMixin
from app.annotation.source_helpers import SourceHelpersMixin
from app.annotation.roi_state import ROIStateMixin
from app.annotation.roi_projection import ROIProjectionMixin
from app.annotation.display_canvas import DisplayCanvasMixin
from app.annotation.display_overlays import DisplayOverlaysMixin
from app.annotation.display_status import DisplayStatusMixin
from app.annotation.mouse_events import MouseEventsMixin
from app.annotation.mode_toggles import ModeTogglesMixin
from app.annotation.frame_pipeline import FramePipelineMixin
from app.annotation.frame_model_helpers import FrameModelHelpersMixin
from app.annotation.tracking_ids import TrackingIdsMixin
from app.annotation.workflow_actions import WorkflowActionsMixin
from app.annotation.review_nav import ReviewNavMixin
from app.annotation.selection_edit import SelectionEditMixin
from app.annotation.persistence import PersistenceMixin


class AnnotationTool(
    CoreInitMixin,
    RuntimeStateMixin,
    UILayoutMixin,
    UIControlsMixin,
    SourceDiscoveryMixin,
    ClassConfigMixin,
    SourceLoadingMixin,
    SourceHelpersMixin,
    ROIStateMixin,
    ROIProjectionMixin,
    DisplayCanvasMixin,
    DisplayOverlaysMixin,
    DisplayStatusMixin,
    MouseEventsMixin,
    ModeTogglesMixin,
    FramePipelineMixin,
    FrameModelHelpersMixin,
    TrackingIdsMixin,
    WorkflowActionsMixin,
    ReviewNavMixin,
    SelectionEditMixin,
    PersistenceMixin
):
    """Classe principal composta por mixins por area funcional."""

    pass
