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


def active_session() -> Optional[SessionState]:
    return next((s for s in _sessions.values() if s.status in {"running", "paused"}), None)


def create_session(**kwargs) -> SessionState:
    session = SessionState(**kwargs)
    _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> Optional[SessionState]:
    return _sessions.get(session_id)


def remove_session(session_id: str) -> Optional[SessionState]:
    session = _sessions.pop(session_id, None)
    if session is not None:
        session.status = "done"
    return session


def create_export(job: ExportJob) -> ExportJob:
    _exports[job.export_id] = job
    return job


def get_export(export_id: str) -> Optional[ExportJob]:
    return _exports.get(export_id)


def reset_state() -> None:
    """Clear API process state for tests and controlled restarts."""
    _sessions.clear()
    _exports.clear()
