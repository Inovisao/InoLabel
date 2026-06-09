from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api.routes.annotations import reset_annotations
from app.api.schemas import (
    ProjectEntry,
    SessionActionRequest,
    SessionActionResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStatusResponse,
    SessionStopResponse,
)
from app.api.state import active_session, create_session, get_session, remove_session
from app.api.state import SessionState as _SessionState
from app.config import IMAGE_EXTENSIONS, IMAGE_LIST_EXTENSIONS, VIDEO_EXTENSIONS

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/session", tags=["session"])


def _update_project_meta(session: _SessionState) -> None:
    """Rewrite .inolabel.json on stop so Projects page shows fresh data."""
    meta_path = session.output_path / ".inolabel.json"
    try:
        meta: dict = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    except Exception:
        meta = {}
    meta.update({
        "mode": session.mode,
        "classes": session.classes,
        "data_path": str(session.data_path),
        "last_modified": datetime.now(timezone.utc).isoformat(),
        "current_frame": session.current_frame,
    })
    try:
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _count_frames(path: Path) -> int:
    """Count annotatable frames under path. May be slow on large datasets — call via run_in_threadpool."""
    if path.is_dir():
        exts = set(IMAGE_EXTENSIONS)
        return sum(1 for child in path.rglob("*") if child.is_file() and child.suffix.lower() in exts)
    if path.suffix.lower() in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + IMAGE_LIST_EXTENSIONS:
        return 1
    return 0


@router.get("/projects", response_model=list[ProjectEntry])
def list_projects(path: str = "output") -> list[ProjectEntry]:
    """Scan a directory for InoLabel project folders and return metadata for each."""
    scan_root = Path(path).expanduser().resolve()
    if not scan_root.exists() or not scan_root.is_dir():
        return []

    candidates: list[Path] = []
    if (scan_root / ".inolabel.json").exists():
        candidates.append(scan_root)
    try:
        for subdir in scan_root.iterdir():
            if subdir.is_dir() and (subdir / ".inolabel.json").exists():
                candidates.append(subdir)
    except PermissionError:
        pass

    projects: list[ProjectEntry] = []
    for output_dir in candidates:
        meta_path = output_dir / ".inolabel.json"
        try:
            meta: dict = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        labels_dir = output_dir / "labels"
        annotated_frames = 0
        mtimes: list[float] = [meta_path.stat().st_mtime]

        if labels_dir.exists():
            try:
                with os.scandir(labels_dir) as it:
                    for entry in it:
                        if entry.name.endswith(".txt") and entry.is_file(follow_symlinks=False):
                            st = entry.stat()
                            mtimes.append(st.st_mtime)
                            if st.st_size > 0:
                                annotated_frames += 1
            except PermissionError:
                pass

        last_modified = datetime.fromtimestamp(
            max(mtimes), tz=timezone.utc
        ).isoformat(timespec="seconds")

        raw_data_path = meta.get("data_path", "")
        data_path = raw_data_path if raw_data_path and Path(raw_data_path).exists() else ""

        projects.append(ProjectEntry(
            name=output_dir.name,
            path=str(output_dir),
            data_path=data_path,
            mode=meta.get("mode", "unknown"),
            annotated_frames=annotated_frames,
            classes=meta.get("classes", []),
            created_at=meta.get("created_at", ""),
            last_modified=last_modified,
        ))

    return sorted(projects, key=lambda p: p.last_modified, reverse=True)


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

    # Read existing metadata early: needed to restore current_frame on resume and
    # to preserve created_at so the project doesn't reset its creation date.
    meta_path = output_path / ".inolabel.json"
    existing_meta: dict = {}
    if meta_path.exists():
        try:
            existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # run_in_threadpool: _count_frames does blocking I/O (rglob) and must not
    # run on the uvicorn async event loop thread directly.
    total = await run_in_threadpool(_count_frames, data_path)

    # Restore last-known frame position on resume; clamp to valid range so a
    # renamed or deleted image file never leaves the index out of bounds.
    restored_frame = 0
    if req.resume:
        try:
            restored_frame = min(
                max(int(existing_meta.get("current_frame", 0)), 0),
                max(total - 1, 0),
            )
        except (TypeError, ValueError):
            pass

    session = create_session(
        mode=req.mode.value,
        data_path=data_path,
        output_path=output_path,
        model_path=model_path,
        resume=req.resume,
        classes=req.classes,
        total_frames=total,
        current_frame=restored_frame,
    )
    log.info(
        "start_session: created session %s mode=%s frames=%d path=%s resume=%s frame=%d",
        session.session_id, session.mode, total, data_path, req.resume, restored_frame,
    )

    # Write project metadata so the Projects page can discover this session later.
    # Preserve created_at from any existing metadata; include current_frame for resume.
    try:
        meta = {
            "session_id": session.session_id,
            "mode": session.mode,
            "data_path": str(data_path),
            "classes": req.classes,
            "current_frame": session.current_frame,
            "created_at": existing_meta.get("created_at") or datetime.now(timezone.utc).isoformat(),
        }
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
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
    _update_project_meta(session)
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
    _update_project_meta(session)
    reset_annotations()
    return {"ok": True}
