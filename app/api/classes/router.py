from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.api.classes.schemas import ClassItem
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
            keypoints=_spec(session, i).get("keypoints", []),
            skeleton=_spec(session, i).get("skeleton", []),
        )
        for i, name in enumerate(session.classes)
    ]


def _spec(session, index: int) -> dict:
    specs = session.keypoint_specs or []
    return specs[index] if index < len(specs) else {}
