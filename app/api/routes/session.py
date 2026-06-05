from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool

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

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/session", tags=["session"])


def _count_frames(path: Path) -> int:
    """Count annotatable frames under path. May be slow on large datasets — call via run_in_threadpool."""
    if path.is_dir():
        exts = set(IMAGE_EXTENSIONS)
        return sum(1 for child in path.rglob("*") if child.is_file() and child.suffix.lower() in exts)
    if path.suffix.lower() in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + IMAGE_LIST_EXTENSIONS:
        return 1
    return 0


@router.post("/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest, background_tasks: BackgroundTasks) -> SessionStartResponse:
    """Validate all inputs first, then stop any running session, then create new session.

    Order is critical: destruction of the existing session must only happen after
    we are certain the new request is valid — otherwise an invalid request would
    silently kill an active session without starting a replacement.
    """
    # --- 1. Validate inputs before touching any state ---
    if req.data_path is None:
        raise HTTPException(status_code=422, detail="Informe data_path.")

    data_path = Path(req.data_path).expanduser().resolve()
    if not data_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"Dataset não encontrado: {data_path}",
        )

    output_path = Path(req.output_path or "outputs").expanduser().resolve()

    model_path: Path | None = None
    if req.model_path:
        model_path = Path(req.model_path).expanduser().resolve()
        if not model_path.exists():
            raise HTTPException(
                status_code=422,
                detail=f"Modelo não encontrado: {model_path}",
            )
        if model_path.suffix.lower() != ".pt":
            raise HTTPException(status_code=422, detail="Modelo deve ser um arquivo .pt válido.")

    # --- 2. Inputs are valid — now it is safe to stop any existing session ---
    existing = active_session()
    if existing is not None:
        log.info("start_session: auto-stopping session %s to start a new one", existing.session_id)
        remove_session(existing.session_id)
        reset_annotations()

    # --- 3. Prepare output directory and reset annotation state ---
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Não foi possível criar a pasta de saída ({output_path}): {exc}",
        ) from exc

    reset_annotations()

    # run_in_threadpool: _count_frames does blocking I/O (rglob) and must not
    # run on the uvicorn async event loop thread directly.
    total = await run_in_threadpool(_count_frames, data_path)

    session = create_session(
        mode=req.mode.value,
        data_path=data_path,
        output_path=output_path,
        model_path=model_path,
        resume=req.resume,
        classes=req.classes,
        total_frames=total,
    )
    log.info(
        "start_session: created session %s mode=%s frames=%d path=%s",
        session.session_id, session.mode, total, data_path,
    )

    # Write project metadata so the Projects page can discover this session later.
    try:
        meta = {
            "session_id": session.session_id,
            "mode": session.mode,
            "data_path": str(data_path),
            "classes": req.classes,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (output_path / ".inolabel.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass  # non-critical — projects page will just miss this entry

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
        return {
            "active": False,
            "session_id": None,
            "total_frames": 0,
            "current_index": 0,
            "classes": [],
            "autosaved": False,
            "data_path": None,
            "output_path": None,
        }
    return {
        "active": True,
        "session_id": session.session_id,
        "mode": session.mode,
        "total_frames": session.total_frames,
        "current_index": session.current_frame,
        "classes": session.classes,
        "autosaved": False,
        "data_path": str(session.data_path),
        "output_path": str(session.output_path),
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
    reset_annotations()  # must mirror stop_session(); legacy endpoint used by frontend
    return {"ok": True}
