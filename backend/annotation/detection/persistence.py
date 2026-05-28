"""Re-exporta PersistenceMixin composto a partir de storage + exporters + lifecycle."""

from backend.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from backend.annotation.infrastructure.persistence.export_actions import ExportActionsMixin
from backend.annotation.application.lifecycle import LifecycleMixin


class PersistenceMixin(CocoStorageMixin, ExportActionsMixin, LifecycleMixin):
    """Composição de armazenamento COCO, exportações e ciclo de vida da sessão."""
    pass
