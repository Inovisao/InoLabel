"""Frame exibido no canvas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.api.common.schemas import Annotation


class FrameResponse(BaseModel):
    index: int
    total: int
    image_b64: str
    filename: str
    annotations: List[Annotation] = []
    is_saved: bool = False
    reviewed: bool = False
    # Modo classificação: índice da classe já atribuída a esta imagem (None = não classificada).
    classification_id: Optional[int] = None
