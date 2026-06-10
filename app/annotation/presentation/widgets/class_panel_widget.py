"""Class panel compatibility mixin.

The React frontend is the primary UI, but legacy Tkinter annotation flows still
compose this mixin with class-management logic.
"""

from __future__ import annotations


class ClassPanelWidgetMixin:
    def update_class_panel(self, *, force: bool = False) -> None:
        snapshot = tuple(getattr(self, "target_classes", []))
        if not force and getattr(self, "_class_panel_snapshot", None) == snapshot:
            return
        self._class_panel_snapshot = snapshot
