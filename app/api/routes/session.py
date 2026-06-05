from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.routes.annotations import reset_annotations
from app.api.schemas import (
    SessionActionRequest,
    SessionActionResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStatusResponse,
    SessionStopResponse,
)
from app.api.state import active_session, create_session, get_session, remove_session
from app.config import IMAGE_EXTENSIONS, IMAGE_LIST_EXTENSIONS, VIDEO_EXTENSIONS

router = APIRouter(prefix="/api/session", tags=["session"])


def _count_frames(path: Path) -> int:
    if path.is_dir():
        exts = set(IMAGE_EXTENSIONS)
        return sum(1 for child in path.rglob("*") if child.is_file() and child.suffix.lower() in exts)
    if path.suffix.lower() in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + IMAGE_LIST_EXTENSIONS:
        return 1
    return 0


@router.post("/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest, background_tasks: BackgroundTasks) -> SessionStartResponse:
    """Create one API session without touching Tkinter runtime state."""
    # Auto-encerra sessão anterior se ainda estiver ativa
    existing = active_session()
    if existing is not None:
        remove_session(existing.session_id)
        reset_annotations()
    if req.data_path is None:
        raise HTTPException(status_code=422, detail="Informe data_path.")

    data_path = Path(req.data_path).expanduser().resolve()
    output_path = Path(req.output_path or "outputs").expanduser().resolve()
    model_path = Path(req.model_path).expanduser() if req.model_path else None
    reset_annotations()
    session = create_session(
        mode=req.mode.value,
        data_path=data_path,
        output_path=output_path,
        model_path=model_path,
        resume=req.resume,
        classes=req.classes,
        total_frames=_count_frames(data_path),
    )
    return SessionStartResponse(
        session_id=session.session_id,
        total_frames=session.total_frames,
        current_frame=session.current_frame,
        mode=req.mode,
        current_index=session.current_frame,
        classes=session.classes,
    )


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
def get_status(session_id: str) -> SessionStatusResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return SessionStatusResponse(
        session_id=session.session_id,
        current_frame=session.current_frame,
        total_frames=session.total_frames,
        saved_frames=session.saved_frames,
        status=session.status,
    )


@router.get("/status")
def get_legacy_status():
    session = active_session()
    if session is None:
        return {"active": False, "total_frames": 0, "current_index": 0, "classes": [], "autosaved": False}
    return {
        "active": True,
        "mode": session.mode,
        "total_frames": session.total_frames,
        "current_index": session.current_frame,
        "classes": session.classes,
        "autosaved": False,
    }


@router.post("/{session_id}/action", response_model=SessionActionResponse)
def run_action(session_id: str, body: SessionActionRequest) -> SessionActionResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    if body.action in {"validate", "reject"}:
        session.saved_frames += 1
        session.current_frame = min(session.current_frame + 1, max(session.total_frames - 1, 0))
    elif body.action == "next":
        session.current_frame = min(session.current_frame + 1, max(session.total_frames - 1, 0))
    elif body.action == "prev":
        session.current_frame = max(session.current_frame - 1, 0)
    elif body.action == "undo":
        session.annotation_count = max(session.annotation_count - 1, 0)
    else:
        raise HTTPException(status_code=422, detail="Ação inválida")

    return SessionActionResponse(
        current_frame=session.current_frame,
        annotation_count=session.annotation_count,
    )


@router.post("/{session_id}/stop", response_model=SessionStopResponse)
def stop_session(session_id: str) -> SessionStopResponse:
    session = remove_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    reset_annotations()
    return SessionStopResponse(
        saved_frames=session.saved_frames,
        output_path=str(session.output_path),
    )


@router.post("/stop")
def stop_legacy_session():
    session = active_session()
    if session is None:
        return {"ok": True}
    remove_session(session.session_id)
    return {"ok": True}
