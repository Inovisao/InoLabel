"""Re-exporta PersistenceMixin composto a partir de storage + exporters + lifecycle."""

from app.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from app.annotation.infrastructure.persistence.export_actions import ExportActionsMixin
from app.annotation.application.lifecycle import LifecycleMixin


class PersistenceMixin(CocoStorageMixin, ExportActionsMixin, LifecycleMixin):
    """Composição de armazenamento COCO, exportações e ciclo de vida da sessão."""
    pass
