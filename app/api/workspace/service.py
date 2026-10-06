"""Workspace de projetos: abrir/criar, listar recentes e criar/atualizar projetos.

A lista de projetos reaproveita a varredura de ``projects.listing`` (contagem de frames
anotados, projetos antigos). Pastas e índice ficam em ``workspace.storage``.
"""

from __future__ import annotations

from pathlib import Path

from app.api.common.errors import InvalidInput
from app.api.projects.listing import list_projects
from app.api.workspace import storage
from app.api.workspace.schemas import (
    WorkspaceInfo,
    WorkspaceOpen,
    WorkspaceOverview,
    WorkspaceProjectCreate,
    WorkspaceProjectCreated,
    WorkspaceProjectUpdate,
    WorkspaceRecent,
)


def _local_dir() -> Path:
    # Lido na chamada: os testes trocam LOCAL_DIR.
    from app import config

    return Path(config.LOCAL_DIR)


def overview() -> WorkspaceOverview:
    """Workspace atual (o mais recente que ainda existe) e a lista de recentes."""
    current = None
    items = []
    for entry in storage.load_recents(_local_dir()):
        exists = Path(entry["path"]).is_dir()
        items.append(WorkspaceRecent(path=entry["path"], name=entry.get("name", ""),
                                     opened_at=entry.get("opened_at", ""), exists=exists))
        if current is None and exists:
            try:
                current = WorkspaceInfo(**storage.load_workspace(Path(entry["path"])))
            except (storage.WorkspaceError, OSError):
                current = None
    return WorkspaceOverview(current=current, recent=items)


def open_workspace(body: WorkspaceOpen) -> WorkspaceInfo:
    try:
        info = storage.create_workspace(Path(body.path), body.name)
    except (storage.WorkspaceError, OSError) as exc:
        raise InvalidInput(str(exc)) from exc
    storage.remember_workspace(_local_dir(), info)
    return WorkspaceInfo(**info)


def projects(path: str) -> list:
    if not Path(path).expanduser().is_absolute():
        raise InvalidInput("Informe o caminho completo do workspace.")
    return list_projects(path)


def create_project(body: WorkspaceProjectCreate) -> WorkspaceProjectCreated:
    try:
        project = storage.create_project(
            Path(body.workspace), name=body.name, mode=body.mode.value,
            data_path=Path(body.data_path), classes=body.classes,
        )
    except (storage.WorkspaceError, OSError) as exc:
        raise InvalidInput(str(exc)) from exc
    return WorkspaceProjectCreated(folder=project.name, output_path=str(project))


def update_project(body: WorkspaceProjectUpdate) -> WorkspaceProjectCreated:
    try:
        storage.update_project(Path(body.workspace), body.folder,
                               data_path=Path(body.data_path) if body.data_path else None)
    except (storage.WorkspaceError, OSError, ValueError) as exc:
        raise InvalidInput(str(exc)) from exc
    output_path = Path(body.workspace).expanduser().resolve() / body.folder
    return WorkspaceProjectCreated(folder=body.folder, output_path=str(output_path))
