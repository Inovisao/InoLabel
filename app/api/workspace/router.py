"""Rotas HTTP do workspace de projetos (modelo Obsidian)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.projects.schemas import ProjectEntry
from app.api.workspace import service
from app.api.workspace.schemas import (
    WorkspaceInfo,
    WorkspaceOpen,
    WorkspaceOverview,
    WorkspaceProjectCreate,
    WorkspaceProjectCreated,
    WorkspaceProjectUpdate,
)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


@router.get("", response_model=WorkspaceOverview)
def get_workspace() -> WorkspaceOverview:
    return service.overview()


@router.post("", response_model=WorkspaceInfo)
def open_workspace(body: WorkspaceOpen) -> WorkspaceInfo:
    return service.open_workspace(body)


@router.get("/projects", response_model=list[ProjectEntry])
def workspace_projects(path: str) -> list:
    return service.projects(path)


@router.post("/projects", response_model=WorkspaceProjectCreated)
def create_workspace_project(body: WorkspaceProjectCreate) -> WorkspaceProjectCreated:
    return service.create_project(body)


@router.patch("/projects", response_model=WorkspaceProjectCreated)
def update_workspace_project(body: WorkspaceProjectUpdate) -> WorkspaceProjectCreated:
    return service.update_project(body)
