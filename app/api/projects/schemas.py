"""Validação de caminhos e listagem de projetos."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel


class PathValidationRequest(BaseModel):
    path: str

class OutputsRequest(BaseModel):
    output_path: str

class ProjectEntry(BaseModel):
    name: str
    path: str
    data_path: str
    mode: str
    annotated_frames: int
    classes: List[str]
    created_at: str
    last_modified: str
