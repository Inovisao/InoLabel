"""Modos de anotação oferecidos pela API."""

from __future__ import annotations


from pydantic import BaseModel

from app.api.common.schemas import TaskMode


class ModeInfo(BaseModel):
    id: TaskMode
    label: str
    description: str
    icon: str
