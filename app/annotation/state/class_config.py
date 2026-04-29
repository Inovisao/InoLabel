"""Re-exporta ClassConfigMixin composto a partir de serviço + widget."""

from app.annotation.core.services.class_service import ClassServiceMixin
from app.annotation.presentation.widgets.class_panel_widget import ClassPanelWidgetMixin


class ClassConfigMixin(ClassServiceMixin, ClassPanelWidgetMixin):
    """Composição de lógica de categorias e widget de painel de classes."""
    pass
