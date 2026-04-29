"""Re-exporta UILayoutMixin composto a partir dos painéis de apresentação."""

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
    """Composição de todos os painéis da interface principal."""
    pass
