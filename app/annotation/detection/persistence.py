"""Re-exports PersistenceMixin composed from storage + exporters + lifecycle."""

from app.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from app.annotation.infrastructure.persistence.export_actions import ExportActionsMixin
from app.annotation.application.lifecycle import LifecycleMixin


class PersistenceMixin(CocoStorageMixin, ExportActionsMixin, LifecycleMixin):
    """Composition of COCO storage, exports and session lifecycle."""
    pass
