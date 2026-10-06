"""Workspace de projetos (modelo Obsidian): pasta escolhida pelo usuário com um índice.

O frontend cria projetos aqui e inicia a sessão com ``output_path`` = pasta do
projeto, sempre absoluta. A lista de projetos reaproveita a varredura de
``validation.list_projects`` (contagem de frames anotados, projetos antigos).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.routes.validation import list_projects
from app.api.schemas import (
    ProjectEntry,
    WorkspaceInfo,
    WorkspaceOpen,
    WorkspaceOverview,
    WorkspaceProjectCreate,
    WorkspaceProjectCreated,
    WorkspaceProjectUpdate,
    WorkspaceRecent,
)
from app.core import workspace as ws

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def _local_dir() -> Path:
    # Lido na chamada: os testes trocam LOCAL_DIR.
    from app import config

    return Path(config.LOCAL_DIR)


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("", response_model=WorkspaceOverview)
def get_workspace() -> WorkspaceOverview:
    """Workspace atual (o mais recente que ainda existe) e a lista de recentes."""
    recents = ws.load_recents(_local_dir())
    current = None
    items = []
    for entry in recents:
        exists = Path(entry["path"]).is_dir()
        items.append(WorkspaceRecent(path=entry["path"], name=entry.get("name", ""),
                                     opened_at=entry.get("opened_at", ""), exists=exists))
        if current is None and exists:
            try:
                current = WorkspaceInfo(**ws.load_workspace(Path(entry["path"])))
            except (ws.WorkspaceError, OSError):
                current = None
    return WorkspaceOverview(current=current, recent=items)


@router.post("", response_model=WorkspaceInfo)
def open_workspace(body: WorkspaceOpen) -> WorkspaceInfo:
    try:
        info = ws.create_workspace(Path(body.path), body.name)
    except (ws.WorkspaceError, OSError) as exc:
        raise _bad_request(exc) from exc
    ws.remember_workspace(_local_dir(), info)
    return WorkspaceInfo(**info)


@router.get("/projects", response_model=list[ProjectEntry])
def workspace_projects(path: str) -> list:
    if not Path(path).expanduser().is_absolute():
        raise HTTPException(status_code=422, detail="Informe o caminho completo do workspace.")
    return list_projects(path)


@router.post("/projects", response_model=WorkspaceProjectCreated)
def create_workspace_project(body: WorkspaceProjectCreate) -> WorkspaceProjectCreated:
    try:
        project = ws.create_project(
            Path(body.workspace), name=body.name, mode=body.mode.value,
            data_path=Path(body.data_path), classes=body.classes,
        )
    except (ws.WorkspaceError, OSError) as exc:
        raise _bad_request(exc) from exc
    return WorkspaceProjectCreated(folder=project.name, output_path=str(project))


@router.patch("/projects", response_model=WorkspaceProjectCreated)
def update_workspace_project(body: WorkspaceProjectUpdate) -> WorkspaceProjectCreated:
    try:
        ws.update_project(Path(body.workspace), body.folder,
                          data_path=Path(body.data_path) if body.data_path else None)
    except (ws.WorkspaceError, OSError, ValueError) as exc:
        raise _bad_request(exc) from exc
    return WorkspaceProjectCreated(folder=body.folder, output_path=str(Path(body.workspace).expanduser().resolve() / body.folder))
