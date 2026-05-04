"""Composicao da ferramenta de anotacao OBB."""

from app.annotation.state.core_init import CoreInitMixin
from app.annotation.core.services.class_service import ClassServiceMixin
from app.annotation.sources.source_discovery import SourceDiscoveryMixin
from app.annotation.sources.source_loading import SourceLoadingMixin
from app.annotation.roi.roi_state import ROIStateMixin
from app.annotation.roi.roi_projection import ROIProjectionMixin
from app.annotation.application.lifecycle import LifecycleMixin
from app.annotation.presentation.panels.main_window import MainWindowMixin
from app.annotation.presentation.panels.topbar_panel import TopbarPanelMixin
from app.annotation.presentation.panels.statusbar_panel import StatusbarPanelMixin
from app.annotation.presentation.panels.sidebar_panel import SidebarPanelMixin
from app.annotation.presentation.panels.canvas_panel import CanvasPanelMixin
from app.annotation.presentation.widgets.class_panel_widget import ClassPanelWidgetMixin
from app.annotation.ui.display_canvas import DisplayCanvasMixin

from app.annotation_obb.state.runtime_state import OBBRuntimeStateMixin
from app.annotation_obb.sources.source_helpers import OBBSourceHelpersMixin
from app.annotation_obb.detection.frame_pipeline import OBBFramePipelineMixin
from app.annotation_obb.detection.frame_model_helpers import OBBFrameModelHelpersMixin
from app.annotation_obb.detection.workflow_actions import OBBWorkflowActionsMixin
from app.annotation_obb.detection.review_nav import OBBReviewNavMixin
from app.annotation_obb.detection.selection_edit import OBBSelectionEditMixin
from app.annotation_obb.infrastructure.persistence.obb_coco_storage import OBBCocoStorageMixin
from app.annotation_obb.infrastructure.persistence.export_actions import OBBExportActionsMixin
from app.annotation_obb.ui.display_canvas import OBBDisplayCanvasMixin
from app.annotation_obb.ui.display_overlays import OBBDisplayOverlaysMixin
from app.annotation_obb.ui.display_status import OBBDisplayStatusMixin
from app.annotation_obb.ui.mouse_events import OBBMouseEventsMixin
from app.annotation_obb.ui.mode_toggles import OBBModeTogglesMixin
from app.annotation_obb.ui.ui_controls import OBBUIControlsMixin


class OBBAnnotationTool(
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
    MainWindowMixin,
    TopbarPanelMixin,
    StatusbarPanelMixin,
    SidebarPanelMixin,
    CanvasPanelMixin,
    ClassPanelWidgetMixin,
    OBBUIControlsMixin,
    OBBDisplayCanvasMixin,
    OBBDisplayOverlaysMixin,
    DisplayCanvasMixin,
    OBBDisplayStatusMixin,
    OBBMouseEventsMixin,
    OBBModeTogglesMixin,
):
    """Ferramenta OBB isolada do fluxo HBB/tracking."""
    pass
