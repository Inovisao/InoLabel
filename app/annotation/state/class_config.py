"""Re-exports ClassConfigMixin composed from service + widget."""

from tkinter import messagebox

from app.annotation.core.services.class_service import ClassServiceMixin
from app.annotation.presentation.widgets.class_panel_widget import ClassPanelWidgetMixin


class ClassConfigMixin(ClassServiceMixin, ClassPanelWidgetMixin):
    """Composition of category logic and the class panel widget."""
    pass
