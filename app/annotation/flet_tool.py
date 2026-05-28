"""Composição da ferramenta de anotação para interface Flet.

Substitui os mixins Tkinter pelos equivalentes Flet, preservando
toda a lógica de negócio da AnnotationTool original.
"""

from __future__ import annotations

import flet as ft

# ── Estado ──────────────────────────────────────────────────────────────────
from app.annotation.state.core_init import CoreInitMixin
from app.annotation.state.runtime_state import RuntimeStateMixin

# ── Domínio ──────────────────────────────────────────────────────────────────
from app.annotation.core.services.class_service import ClassServiceMixin

# ── Fontes ───────────────────────────────────────────────────────────────────
from app.annotation.sources.source_discovery import SourceDiscoveryMixin
from app.annotation.sources.source_loading import SourceLoadingMixin
from app.annotation.sources.source_helpers import SourceHelpersMixin

# ── ROI ──────────────────────────────────────────────────────────────────────
from app.annotation.roi.roi_state import ROIStateMixin
from app.annotation.roi.roi_projection import ROIProjectionMixin

# ── Detecção ─────────────────────────────────────────────────────────────────
from app.annotation.detection.frame_pipeline import FramePipelineMixin
from app.annotation.detection.frame_model_helpers import FrameModelHelpersMixin
from app.annotation.detection.tracking_ids import TrackingIdsMixin
from app.annotation.detection.workflow_actions import WorkflowActionsMixin
from app.annotation.detection.review_nav import ReviewNavMixin
from app.annotation.detection.selection_edit import SelectionEditMixin

# ── Infraestrutura ───────────────────────────────────────────────────────────
from app.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from app.annotation.infrastructure.persistence.export_actions import ExportActionsMixin

# ── Ciclo de vida ─────────────────────────────────────────────────────────────
from app.annotation.application.lifecycle import LifecycleMixin

# ── UI Flet: janela e painéis ────────────────────────────────────────────────
from app.annotation.presentation.panels.flet_main_window import FletMainWindowMixin
from app.annotation.presentation.panels.flet_topbar import FletTopbarPanelMixin
from app.annotation.presentation.panels.flet_statusbar import FletStatusbarPanelMixin
from app.annotation.presentation.panels.flet_sidebar import FletSidebarPanelMixin
from app.annotation.presentation.panels.flet_canvas_panel import FletCanvasPanelMixin

# ── UI Flet: widgets ─────────────────────────────────────────────────────────
from app.annotation.presentation.widgets.class_panel_widget import ClassPanelWidgetMixin

# ── UI Flet: controles e renderização ────────────────────────────────────────
from app.annotation.flet_ui.ui_controls import FletUIControlsMixin
from app.annotation.flet_ui.display import FletDisplayCanvasMixin
from app.annotation.ui.display_overlays import DisplayOverlaysMixin
from app.annotation.ui.display_status import DisplayStatusMixin
from app.annotation.flet_ui.mouse import FletMouseEventsMixin
from app.annotation.flet_ui.mode_toggles import FletModeTogglesMixin

# ── Export screen (mantido Tkinter internamente, exibido no canvas_area) ─────
from app.annotation.presentation.export.export_screen import ExportScreenMixin


class FletAnnotationTool(
    # Estado
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
    # UI Flet — janela e painéis
    FletMainWindowMixin,
    FletTopbarPanelMixin,
    FletStatusbarPanelMixin,
    FletSidebarPanelMixin,
    FletCanvasPanelMixin,
    ExportScreenMixin,
    # UI Flet — widgets
    ClassPanelWidgetMixin,
    # UI Flet — controles e renderização
    FletUIControlsMixin,
    FletDisplayCanvasMixin,
    DisplayOverlaysMixin,
    DisplayStatusMixin,
    FletMouseEventsMixin,
    FletModeTogglesMixin,
):
    """
    Ferramenta de anotação com interface Flet.

    Composição idêntica à AnnotationTool original, mas com os mixins
    de UI Tkinter substituídos pelos equivalentes Flet.
    """

    def __init__(self, *, session_config, page: ft.Page, **kwargs):
        self.page = page  # Definido antes de super().__init__() para que _build_ui() funcione
        super().__init__(session_config=session_config, **kwargs)
