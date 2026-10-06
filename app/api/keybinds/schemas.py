"""Perfil de atalhos de teclado."""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel


class KeybindProfile(BaseModel):
    profile: str
    binds: Dict[str, str]


class KeybindProfiles(BaseModel):
    active_profile: str
    profiles: Dict[str, Dict[str, list[str]]]
