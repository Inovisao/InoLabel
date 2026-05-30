"""Re-exports UILayoutMixin composed from the presentation panels."""

from app.annotation.presentation.panels.main_window import MainWindowMixin
from app.annotation.presentation.panels.topbar_panel import TopbarPanelMixin
from app.annotation.presentation.panels.statusbar_panel import StatusbarPanelMixin
from app.annotation.presentation.panels.sidebar_panel import SidebarPanelMixin
from app.annotation.presentation.panels.canvas_panel import CanvasPanelMixin


class UILayoutMixin(
    MainWindowMixin,
    TopbarPanelMixin,
    StatusbarPanelMixin,
    SidebarPanelMixin,
    CanvasPanelMixin,
):
    """Composition of all panels of the main interface."""
    pass
