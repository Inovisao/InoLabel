"""Composition of the main annotation tool."""

# ── State ────────────────────────────────────────────────────────────────────
from app.annotation.state.core_init import CoreInitMixin
from app.annotation.state.runtime_state import RuntimeStateMixin

# ── Domain: categories ───────────────────────────────────────────────────────
from app.annotation.core.services.class_service import ClassServiceMixin

# ── Media sources ────────────────────────────────────────────────────────────
from app.annotation.sources.source_discovery import SourceDiscoveryMixin
from app.annotation.sources.source_loading import SourceLoadingMixin
from app.annotation.sources.source_helpers import SourceHelpersMixin

# ── ROI and homography ───────────────────────────────────────────────────────
from app.annotation.roi.roi_state import ROIStateMixin
from app.annotation.roi.roi_projection import ROIProjectionMixin

# ── Detection and tracking ───────────────────────────────────────────────────
from app.annotation.detection.frame_pipeline import FramePipelineMixin
from app.annotation.detection.frame_model_helpers import FrameModelHelpersMixin
from app.annotation.detection.tracking_ids import TrackingIdsMixin
from app.annotation.detection.workflow_actions import WorkflowActionsMixin
from app.annotation.detection.review_nav import ReviewNavMixin
from app.annotation.detection.selection_edit import SelectionEditMixin

# ── Infrastructure: persistence ──────────────────────────────────────────────
from app.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from app.annotation.infrastructure.persistence.export_actions import ExportActionsMixin

# ── Application: lifecycle ───────────────────────────────────────────────────
from app.annotation.application.lifecycle import LifecycleMixin

# ── Presentation: window and panels ──────────────────────────────────────────
from app.annotation.presentation.panels.main_window import MainWindowMixin
from app.annotation.presentation.panels.topbar_panel import TopbarPanelMixin
from app.annotation.presentation.panels.statusbar_panel import StatusbarPanelMixin
from app.annotation.presentation.panels.sidebar_panel import SidebarPanelMixin
from app.annotation.presentation.panels.canvas_panel import CanvasPanelMixin
from app.annotation.presentation.export.export_screen import ExportScreenMixin

# ── Presentation: widgets ─────────────────────────────────────────────────────
from app.annotation.presentation.widgets.class_panel_widget import ClassPanelWidgetMixin

# ── Presentation: controls and rendering ─────────────────────────────────────
from app.annotation.ui.ui_controls import UIControlsMixin
from app.annotation.ui.display_canvas import DisplayCanvasMixin
from app.annotation.ui.display_overlays import DisplayOverlaysMixin
from app.annotation.ui.display_status import DisplayStatusMixin
from app.annotation.ui.mouse_events import MouseEventsMixin
from app.annotation.ui.mode_toggles import ModeTogglesMixin


class AnnotationTool(
    # Base state
    CoreInitMixin,
    RuntimeStateMixin,
    # Domain
    ClassServiceMixin,
    # Sources
    SourceDiscoveryMixin,
    SourceLoadingMixin,
    SourceHelpersMixin,
    # ROI
    ROIStateMixin,
    ROIProjectionMixin,
    # Detection
    FramePipelineMixin,
    FrameModelHelpersMixin,
    TrackingIdsMixin,
    WorkflowActionsMixin,
    ReviewNavMixin,
    SelectionEditMixin,
    # Infrastructure
    CocoStorageMixin,
    ExportActionsMixin,
    # Lifecycle
    LifecycleMixin,
    # UI — window and panels
    MainWindowMixin,
    TopbarPanelMixin,
    StatusbarPanelMixin,
    SidebarPanelMixin,
    CanvasPanelMixin,
    ExportScreenMixin,
    # UI — widgets
    ClassPanelWidgetMixin,
    # UI — controls and rendering
    UIControlsMixin,
    DisplayCanvasMixin,
    DisplayOverlaysMixin,
    DisplayStatusMixin,
    MouseEventsMixin,
    ModeTogglesMixin,
):
    """
    Main annotation class.

    Layered composition:
      state → domain → sources → roi → detection
      → infrastructure → application → presentation
    """
    pass
