"""Composicao da ferramenta principal de anotacao."""

from app.annotation.state.core_init import CoreInitMixin
from app.annotation.state.runtime_state import RuntimeStateMixin
from app.annotation.state.class_config import ClassConfigMixin

from app.annotation.ui.ui_layout import UILayoutMixin
from app.annotation.ui.ui_controls import UIControlsMixin
from app.annotation.ui.display_canvas import DisplayCanvasMixin
from app.annotation.ui.display_overlays import DisplayOverlaysMixin
from app.annotation.ui.display_status import DisplayStatusMixin
from app.annotation.ui.mouse_events import MouseEventsMixin
from app.annotation.ui.mode_toggles import ModeTogglesMixin

from app.annotation.sources.source_discovery import SourceDiscoveryMixin
from app.annotation.sources.source_loading import SourceLoadingMixin
from app.annotation.sources.source_helpers import SourceHelpersMixin

from app.annotation.roi.roi_state import ROIStateMixin
from app.annotation.roi.roi_projection import ROIProjectionMixin

from app.annotation.detection.frame_pipeline import FramePipelineMixin
from app.annotation.detection.frame_model_helpers import FrameModelHelpersMixin
from app.annotation.detection.tracking_ids import TrackingIdsMixin
from app.annotation.detection.workflow_actions import WorkflowActionsMixin
from app.annotation.detection.review_nav import ReviewNavMixin
from app.annotation.detection.selection_edit import SelectionEditMixin
from app.annotation.detection.persistence import PersistenceMixin


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
