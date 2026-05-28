"""ClassConfigMixin para o backend — alias de ClassServiceMixin sem dependencias de UI."""

from backend.annotation.core.services.class_service import ClassServiceMixin


class ClassConfigMixin(ClassServiceMixin):
    pass
