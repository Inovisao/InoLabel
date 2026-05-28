"""Endpoints de frame: aceitar, rejeitar, deteccoes manuais, ROI."""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models import Detection
from backend.services.session_manager import session_manager

router = APIRouter(prefix="/api/frame", tags=["frame"])


# ── Modelos ──────────────────────────────────────────────────────────────────

class ManualDetectionRequest(BaseModel):
    bbox: List[float]          # [x1, y1, x2, y2] em coordenadas de imagem
    category_id: int
    track_id: Optional[int] = None


class EditDetectionRequest(BaseModel):
    source: str                # "model" | "manual"
    index: int
    category_id: Optional[int] = None
    track_id: Optional[int] = None
    bbox: Optional[List[float]] = None


class ROIRequest(BaseModel):
    points: List[Tuple[float, float]]  # 4 pontos [(x,y), ...]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_tool():
    tool = session_manager.tool
    if tool is None:
        raise HTTPException(400, "Nenhuma sessao ativa. Chame POST /api/session/start primeiro.")
    return tool


def _state_response():
    state = session_manager.get_state()
    session_manager.notify_frame_update()
    return state


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
async def get_current_frame():
    """Retorna o frame atual com base64 + estado completo."""
    _require_tool()
    return session_manager.get_state()


@router.post("/accept")
async def accept_frame():
    """Valida o frame atual e avanca para o proximo."""
    tool = _require_tool()
    try:
        tool.on_accept()
    except Exception as exc:
        raise HTTPException(500, str(exc))
    return _state_response()


@router.post("/reject")
async def reject_frame():
    """Rejeita/pula o frame atual."""
    tool = _require_tool()
    tool.on_reject()
    return _state_response()


@router.post("/undo")
async def undo():
    """Desfaz a ultima acao no frame atual."""
    tool = _require_tool()
    if hasattr(tool, "undo_last_action"):
        tool.undo_last_action()
    elif hasattr(tool, "undo"):
        tool.undo()
    return _state_response()


@router.post("/manual-detection")
async def add_manual_detection(req: ManualDetectionRequest):
    """Adiciona uma deteccao manual ao frame atual."""
    tool = _require_tool()
    bbox = np.array(req.bbox, dtype=np.float32)
    det = Detection(
        original_bbox=bbox,
        warp_bbox=None,
        confidence=1.0,
        category_id=req.category_id,
        track_id=req.track_id,
        source="manual",
        internal_id=None,
    )
    if hasattr(tool, "push_undo_state"):
        tool.push_undo_state("adicionar manual")
    tool.manual_detections.append(det)
    return _state_response()


@router.delete("/detection")
async def remove_detection(source: str, index: int):
    """Remove uma deteccao pelo source e indice."""
    tool = _require_tool()
    dets = tool.manual_detections if source == "manual" else tool.current_detections
    if index < 0 or index >= len(dets):
        raise HTTPException(400, "Indice de deteccao invalido.")
    if hasattr(tool, "push_undo_state"):
        tool.push_undo_state("remover deteccao")
    det = dets.pop(index)
    if hasattr(tool, "remove_detection_from_runtime_state"):
        tool.remove_detection_from_runtime_state(det)
    tool.selected_detection = None
    return _state_response()


@router.put("/detection")
async def edit_detection(req: EditDetectionRequest):
    """Edita categoria, track_id ou bbox de uma deteccao."""
    tool = _require_tool()
    dets = tool.manual_detections if req.source == "manual" else tool.current_detections
    if req.index < 0 or req.index >= len(dets):
        raise HTTPException(400, "Indice invalido.")
    if hasattr(tool, "push_undo_state"):
        tool.push_undo_state("editar deteccao")
    det = dets[req.index]
    if req.category_id is not None:
        det.category_id = req.category_id
    if req.track_id is not None:
        det.track_id = req.track_id
    if req.bbox is not None:
        det.original_bbox = np.array(req.bbox, dtype=np.float32)
    return _state_response()


@router.post("/select")
async def select_detection(source: str, index: int):
    """Seleciona uma deteccao para edicao de ID."""
    tool = _require_tool()
    tool.selected_detection = (source, index)
    return _state_response()


@router.delete("/select")
async def clear_selection():
    tool = _require_tool()
    tool.selected_detection = None
    return _state_response()


# ── ROI ──────────────────────────────────────────────────────────────────────

@router.post("/roi")
async def set_roi(req: ROIRequest):
    """Define os 4 pontos do ROI e calcula a homografia."""
    tool = _require_tool()
    if not hasattr(tool, "roi_points"):
        raise HTTPException(400, "Modo atual nao suporta ROI.")
    if len(req.points) != 4:
        raise HTTPException(400, "ROI requer exatamente 4 pontos.")
    tool.roi_points = list(req.points)
    if hasattr(tool, "_compute_homography"):
        tool._compute_homography()
    return _state_response()


@router.delete("/roi")
async def reset_roi():
    """Limpa o ROI definido."""
    tool = _require_tool()
    if hasattr(tool, "reset_roi"):
        tool.reset_roi()
    return _state_response()


# ── Navegacao entre fontes ───────────────────────────────────────────────────

@router.post("/source/{index}")
async def switch_source(index: int):
    """Muda para uma fonte de dados (video/pasta) pelo indice."""
    tool = _require_tool()
    if index < 0 or index >= len(tool.video_files):
        raise HTTPException(400, "Indice de fonte invalido.")
    tool.start_video(index)
    return _state_response()


@router.post("/rotate")
async def rotate_frame(direction: str = "cw"):
    """Rotaciona a exibicao do frame (cw = horario, ccw = anti-horario)."""
    tool = _require_tool()
    if direction == "cw" and hasattr(tool, "rotate_frame_cw"):
        tool.rotate_frame_cw()
    elif direction == "ccw" and hasattr(tool, "rotate_frame_ccw"):
        tool.rotate_frame_ccw()
    return _state_response()
