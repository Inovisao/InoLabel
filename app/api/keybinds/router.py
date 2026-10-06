"""Rotas HTTP dos atalhos de teclado."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.keybinds import storage
from app.api.keybinds.schemas import KeybindProfile

router = APIRouter(prefix="/api/keybinds", tags=["keybinds"])


@router.get("", response_model=KeybindProfile)
def get_keybinds() -> KeybindProfile:
    return storage.load()


@router.post("", response_model=KeybindProfile)
def save_keybinds(body: KeybindProfile) -> KeybindProfile:
    return storage.save(body)
