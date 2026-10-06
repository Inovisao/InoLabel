"""Workspace de projetos (modelo Obsidian)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.api.common.schemas import TaskMode


class WorkspaceOpen(BaseModel):
    """Abre a pasta como workspace; cria o índice se ainda não for um."""

    path: str
    name: Optional[str] = None

class WorkspaceProjectRef(BaseModel):
    folder: str
    name: str
    mode: str = ""
    created_at: str = ""

class WorkspaceInfo(BaseModel):
    path: str
    name: str
    version: int = 1
    created_at: str = ""
    projects: List[WorkspaceProjectRef] = Field(default_factory=list)

class WorkspaceRecent(BaseModel):
    path: str
    name: str
    opened_at: str = ""
    exists: bool = True

class WorkspaceOverview(BaseModel):
    current: Optional[WorkspaceInfo] = None
    recent: List[WorkspaceRecent] = Field(default_factory=list)

class WorkspaceProjectCreate(BaseModel):
    workspace: str
    name: str
    mode: TaskMode
    data_path: str
    classes: List[str]

class WorkspaceProjectUpdate(BaseModel):
    workspace: str
    folder: str
    data_path: Optional[str] = None

class WorkspaceProjectCreated(BaseModel):
    folder: str
    output_path: str
