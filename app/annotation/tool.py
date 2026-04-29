"""Composição da ferramenta principal de anotação."""

# ── Estado ──────────────────────────────────────────────────────────────────
from app.annotation.state.core_init import CoreInitMixin
from app.annotation.state.runtime_state import RuntimeStateMixin

# ── Domínio: categorias ──────────────────────────────────────────────────────
from app.annotation.core.services.class_service import ClassServiceMixin

# ── Fontes de mídia ──────────────────────────────────────────────────────────
from app.annotation.sources.source_discovery import SourceDiscoveryMixin
from app.annotation.sources.source_loading import SourceLoadingMixin
from app.annotation.sources.source_helpers import SourceHelpersMixin

# ── ROI e homografia ─────────────────────────────────────────────────────────
from app.annotation.roi.roi_state import ROIStateMixin
from app.annotation.roi.roi_projection import ROIProjectionMixin

# ── Detecção e rastreamento ──────────────────────────────────────────────────
from app.annotation.detection.frame_pipeline import FramePipelineMixin
from app.annotation.detection.frame_model_helpers import FrameModelHelpersMixin
from app.annotation.detection.tracking_ids import TrackingIdsMixin
from app.annotation.detection.workflow_actions import WorkflowActionsMixin
from app.annotation.detection.review_nav import ReviewNavMixin
from app.annotation.detection.selection_edit import SelectionEditMixin

# ── Infraestrutura: persistência ─────────────────────────────────────────────
from app.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from app.annotation.infrastructure.persistence.export_actions import ExportActionsMixin

# ── Aplicação: ciclo de vida ─────────────────────────────────────────────────
from app.annotation.application.lifecycle import LifecycleMixin

# ── Apresentação: janela e painéis ───────────────────────────────────────────
from app.annotation.presentation.panels.main_window import MainWindowMixin
from app.annotation.presentation.panels.topbar_panel import TopbarPanelMixin
from app.annotation.presentation.panels.statusbar_panel import StatusbarPanelMixin
from app.annotation.presentation.panels.sidebar_panel import SidebarPanelMixin
from app.annotation.presentation.panels.canvas_panel import CanvasPanelMixin

# ── Apresentação: widgets ────────────────────────────────────────────────────
from app.annotation.presentation.widgets.class_panel_widget import ClassPanelWidgetMixin

# ── Apresentação: controles e renderização ───────────────────────────────────
from app.annotation.ui.ui_controls import UIControlsMixin
from app.annotation.ui.display_canvas import DisplayCanvasMixin
from app.annotation.ui.display_overlays import DisplayOverlaysMixin
from app.annotation.ui.display_status import DisplayStatusMixin
from app.annotation.ui.mouse_events import MouseEventsMixin
from app.annotation.ui.mode_toggles import ModeTogglesMixin


class AnnotationTool(
    # Estado base
    CoreInitMixin,
    RuntimeStateMixin,
    # Domínio
    ClassServiceMixin,
    # Fontes
    SourceDiscoveryMixin,
    SourceLoadingMixin,
    SourceHelpersMixin,
    # ROI
    ROIStateMixin,
    ROIProjectionMixin,
    # Detecção
    FramePipelineMixin,
    FrameModelHelpersMixin,
    TrackingIdsMixin,
    WorkflowActionsMixin,
    ReviewNavMixin,
    SelectionEditMixin,
    # Infraestrutura
    CocoStorageMixin,
    ExportActionsMixin,
    # Ciclo de vida
    LifecycleMixin,
    # UI — janela e painéis
    MainWindowMixin,
    TopbarPanelMixin,
    StatusbarPanelMixin,
    SidebarPanelMixin,
    CanvasPanelMixin,
    # UI — widgets
    ClassPanelWidgetMixin,
    # UI — controles e renderização
    UIControlsMixin,
    DisplayCanvasMixin,
    DisplayOverlaysMixin,
    DisplayStatusMixin,
    MouseEventsMixin,
    ModeTogglesMixin,
):
    """
    Classe principal de anotação.

    Composição por camadas:
      estado → domínio → fontes → roi → detecção
      → infraestrutura → aplicação → apresentação
    """
    pass
