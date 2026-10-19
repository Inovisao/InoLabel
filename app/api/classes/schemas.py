"""Classes da sessão ativa."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ClassItem(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    # Modo keypoint: nomes dos pontos e esqueleto da classe.
    keypoints: List[str] = Field(default_factory=list)
    skeleton: List[List[int]] = Field(default_factory=list)


class ClassCreate(BaseModel):
    name: str
    # Modo keypoint: nomes dos pontos, na ordem em que são clicados (obrigatório nesse modo).
    keypoints: List[str] = Field(default_factory=list)


class ClassRename(BaseModel):
    name: str


class ClassUsage(BaseModel):
    """Quanto do projeto usa a classe: mostrado antes de removê-la."""

    id: int
    name: str
    annotations: int
    frames: int
