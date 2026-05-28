"""Endpoints de ciclo de vida da sessao."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.session import AnnotationSessionConfig, AnnotationTaskMode, normalize_class_names
from backend.core.output_state import create_new_output_dir, load_annotation_state, find_annotations_path
from backend.services.session_manager import session_manager

router = APIRouter(prefix="/api/session", tags=["session"])


# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    mode: str
    data_root: str
    weights_paths: List[str] = []
    target_classes: List[str]
    output_dir: Optional[str] = None
    annotations_path: Optional[str] = None
    resume_existing_annotations: bool = False
    category_metadata: List[Dict[str, Any]] = []
    confidence_threshold: float = 0.40


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_session(req: StartSessionRequest):
    """Inicia uma nova sessao de anotacao."""
    try:
        mode = AnnotationTaskMode(req.mode)
    except ValueError:
        raise HTTPException(400, f"Modo invalido: {req.mode}")

    data_root = Path(req.data_root).expanduser()
    if not data_root.exists():
        raise HTTPException(400, f"Pasta de dados nao encontrada: {data_root}")

    weights_paths = tuple(Path(p).expanduser() for p in req.weights_paths)

    if req.output_dir:
        output_dir = Path(req.output_dir).expanduser()
    else:
        output_dir = create_new_output_dir(task_mode=mode)

    annotations_path = Path(req.annotations_path).expanduser() if req.annotations_path else None

    config = AnnotationSessionConfig(
        mode=mode,
        data_root=data_root,
        weights_paths=weights_paths,
        target_classes=tuple(req.target_classes),
        output_dir=output_dir,
        annotations_path=annotations_path,
        resume_existing_annotations=req.resume_existing_annotations,
        category_metadata=tuple(req.category_metadata),
        confidence_threshold=req.confidence_threshold,
    )

    try:
        session_manager.start(config)
    except Exception as exc:
        raise HTTPException(500, str(exc))

    return session_manager.get_state()


@router.get("/state")
async def get_session_state():
    """Retorna o estado atual da sessao."""
    if not session_manager.active:
        return {"active": False}
    return session_manager.get_state()


@router.delete("")
async def stop_session():
    """Encerra a sessao ativa."""
    session_manager.stop()
    return {"stopped": True}
