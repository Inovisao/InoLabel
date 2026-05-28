"""Composição da ferramenta OBB para interface Flet."""

from __future__ import annotations

import flet as ft

# ── Estado ────────────────────────────────────────────────────────────────────
from app.annotation.state.core_init import CoreInitMixin
from app.annotation_obb.state.runtime_state import OBBRuntimeStateMixin

# ── Domínio ───────────────────────────────────────────────────────────────────
from app.annotation.core.services.class_service import ClassServiceMixin

# ── Fontes ────────────────────────────────────────────────────────────────────
from app.annotation.sources.source_discovery import SourceDiscoveryMixin
from app.annotation.sources.source_loading import SourceLoadingMixin
from app.annotation_obb.sources.source_helpers import OBBSourceHelpersMixin

# ── ROI ───────────────────────────────────────────────────────────────────────
from app.annotation.roi.roi_state import ROIStateMixin
from app.annotation.roi.roi_projection import ROIProjectionMixin

# ── Detecção OBB ──────────────────────────────────────────────────────────────
from app.annotation_obb.detection.frame_pipeline import OBBFramePipelineMixin
from app.annotation_obb.detection.frame_model_helpers import OBBFrameModelHelpersMixin
from app.annotation_obb.detection.workflow_actions import OBBWorkflowActionsMixin
from app.annotation_obb.detection.review_nav import OBBReviewNavMixin
from app.annotation_obb.detection.selection_edit import OBBSelectionEditMixin

# ── Infraestrutura ────────────────────────────────────────────────────────────
from app.annotation_obb.infrastructure.persistence.obb_coco_storage import OBBCocoStorageMixin
from app.annotation_obb.infrastructure.persistence.export_actions import OBBExportActionsMixin

# ── Ciclo de vida ─────────────────────────────────────────────────────────────
from app.annotation.application.lifecycle import LifecycleMixin

# ── UI Flet — painéis genéricos (reutilizados do modo HBB) ───────────────────
from app.annotation.presentation.panels.flet_main_window import FletMainWindowMixin
from app.annotation.presentation.panels.flet_topbar import FletTopbarPanelMixin
from app.annotation.presentation.panels.flet_statusbar import FletStatusbarPanelMixin
from app.annotation.presentation.panels.flet_sidebar import FletSidebarPanelMixin
from app.annotation.presentation.panels.flet_canvas_panel import FletCanvasPanelMixin
from app.annotation.presentation.widgets.class_panel_widget import ClassPanelWidgetMixin
from app.annotation.presentation.export.export_screen import ExportScreenMixin

# ── UI Flet — OBB específico ─────────────────────────────────────────────────
from app.annotation_obb.flet_ui.ui_controls import FletOBBUIControlsMixin
from app.annotation_obb.flet_ui.display import FletOBBDisplayCanvasMixin
from app.annotation_obb.ui.display_overlays import OBBDisplayOverlaysMixin
from app.annotation_obb.ui.display_status import OBBDisplayStatusMixin
from app.annotation_obb.flet_ui.mouse import FletOBBMouseEventsMixin
from app.annotation_obb.flet_ui.mode_toggles import FletOBBModeTogglesMixin


class FletOBBAnnotationTool(
    # Estado
    CoreInitMixin,
    OBBRuntimeStateMixin,
    # Domínio
    ClassServiceMixin,
    # Fontes
    SourceDiscoveryMixin,
    OBBCocoStorageMixin,
    SourceLoadingMixin,
    OBBSourceHelpersMixin,
    # ROI
    ROIStateMixin,
    ROIProjectionMixin,
    # Detecção
    OBBFramePipelineMixin,
    OBBFrameModelHelpersMixin,
    OBBWorkflowActionsMixin,
    OBBReviewNavMixin,
    OBBSelectionEditMixin,
    OBBExportActionsMixin,
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
    # UI Flet — OBB: controls primeiro para garantir MRO de _config_if_changed
    FletOBBUIControlsMixin,
    FletOBBDisplayCanvasMixin,
    OBBDisplayOverlaysMixin,
    OBBDisplayStatusMixin,
    FletOBBMouseEventsMixin,
    FletOBBModeTogglesMixin,
):
    """
    Ferramenta de anotação OBB com interface Flet.

    Composição análoga à OBBAnnotationTool, com os mixins de UI Tkinter
    substituídos pelos equivalentes Flet.
    """

    def __init__(self, *, session_config, page: ft.Page, **kwargs):
        self.page = page  # Definido antes de super().__init__() para que _build_ui() funcione
        super().__init__(session_config=session_config, **kwargs)
