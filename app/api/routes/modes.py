from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import ModeInfo

router = APIRouter(prefix="/api", tags=["modes"])


@router.get("/modes", response_model=list[ModeInfo])
def list_modes() -> list[ModeInfo]:
    return [
        ModeInfo(
            id="tracking",
            label="Rastreamento",
            description="Mantém identidade dos objetos entre frames via BYTETracker por classe.",
            icon="route",
        ),
        ModeInfo(
            id="detection",
            label="Detecção padrão",
            description="Bounding boxes independentes por frame, sem track_id.",
            icon="box",
        ),
        ModeInfo(
            id="obb",
            label="Detecção orientada (OBB)",
            description="Caixas rotacionadas com ângulo, exportáveis no formato YOLO OBB.",
            icon="box-rotate-clockwise",
        ),
        ModeInfo(
            id="classification",
            label="Classificação",
            description="Copia imagens para subpastas por classe ao pressionar o atalho da classe.",
            icon="tag",
        ),
    ]
