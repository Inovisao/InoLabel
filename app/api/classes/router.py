from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.api.classes import service
from app.api.classes.schemas import ClassCreate, ClassItem, ClassRename, ClassUsage

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get("/", response_model=List[ClassItem])
def list_classes() -> List[ClassItem]:
    return service.list_classes()


@router.post("/", response_model=List[ClassItem])
def add_class(body: ClassCreate) -> List[ClassItem]:
    """Nova classe no fim da lista; devolve a lista atualizada."""
    return service.add_class(body)


@router.patch("/{class_id}", response_model=List[ClassItem])
def rename_class(class_id: int, body: ClassRename) -> List[ClassItem]:
    return service.rename_class(class_id, body)


@router.get("/{class_id}/usage", response_model=ClassUsage)
def class_usage(class_id: int) -> ClassUsage:
    """Anotações e frames da classe no projeto (para confirmar a remoção)."""
    return service.class_usage(class_id)


@router.delete("/{class_id}", response_model=List[ClassItem])
def remove_class(class_id: int) -> List[ClassItem]:
    """Remove a classe e as anotações dela; as classes seguintes descem uma posição."""
    return service.remove_class(class_id)
