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
