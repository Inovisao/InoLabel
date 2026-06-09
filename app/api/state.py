"""In-process state isolated to the FastAPI backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.core.exporter import ExportJob


@dataclass
class SessionState:
    """Runtime state for one API annotation session."""

    mode: str
    data_path: Path
    output_path: Path
    classes: list[str]
    model_path: Optional[Path] = None
    resume: bool = False
    session_id: str = field(default_factory=lambda: str(uuid4()))
    current_frame: int = 0
    total_frames: int = 0
    saved_frames: int = 0
    annotation_count: int = 0
    status: str = "running"


# Coexistence: these registries are scoped only to the uvicorn process. Tkinter
# tools keep their own runtime state and are never imported by app.api routes.
_sessions: dict[str, SessionState] = {}
_exports: dict[str, ExportJob] = {}
# Cached ID of the currently active session — avoids O(n) scan on every request.
_active_session_id: Optional[str] = None

# Shared frame state — written by frames.py, read by annotations.py for autosave/load
frame_paths: list[Path] = []
frame_dims: dict[int, tuple[int, int]] = {}  # frame_index → (width, height)

# Annotation store — shared between annotations.py (write) and frames.py (read)
# Keyed by frame index (int). Using a plain dict to avoid any module-level import ambiguity.
annotation_store: dict[int, list] = {}
next_ann_id: list[int] = [1]  # list so it's mutable from any module without 'global'


def active_session() -> Optional[SessionState]:
    global _active_session_id
    if _active_session_id is not None:
        s = _sessions.get(_active_session_id)
        if s is not None and s.status in {"running", "paused"}:
            return s
        _active_session_id = None
    for s in _sessions.values():
        if s.status in {"running", "paused"}:
            _active_session_id = s.session_id
            return s
    return None


def create_session(**kwargs) -> SessionState:
    global _active_session_id
    session = SessionState(**kwargs)
    _sessions[session.session_id] = session
    _active_session_id = session.session_id
    return session


def get_session(session_id: str) -> Optional[SessionState]:
    return _sessions.get(session_id)


def remove_session(session_id: str) -> Optional[SessionState]:
    global _active_session_id
    session = _sessions.pop(session_id, None)
    if session is not None:
        session.status = "done"
        if _active_session_id == session_id:
            _active_session_id = None
    return session


def create_export(job: ExportJob) -> ExportJob:
    _exports[job.export_id] = job
    return job


def get_export(export_id: str) -> Optional[ExportJob]:
    return _exports.get(export_id)


def reset_state() -> None:
    """Clear API process state for tests and controlled restarts."""
    global _active_session_id
    _sessions.clear()
    _exports.clear()
    frame_paths.clear()
    frame_dims.clear()
    annotation_store.clear()
    next_ann_id[0] = 1
    _active_session_id = None
