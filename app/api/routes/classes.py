from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.api.schemas import ClassItem
from app.api.state import active_session
from app.core.palette import CLASS_COLORS

router = APIRouter(prefix="/api/classes", tags=["classes"])

_PALETTE = CLASS_COLORS


@router.get("/", response_model=List[ClassItem])
def list_classes() -> List[ClassItem]:
    session = active_session()
    if session is None:
        return []
    return [
        ClassItem(
            id=i,
            name=name,
            color=_PALETTE[i % len(_PALETTE)],
        )
        for i, name in enumerate(session.classes)
    ]
