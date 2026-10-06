"""Rotas HTTP dos atalhos de teclado."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.keybinds import storage
from app.api.keybinds.schemas import KeybindProfile, KeybindProfiles

router = APIRouter(prefix="/api/keybinds", tags=["keybinds"])


@router.get("/profiles", response_model=KeybindProfiles)
def get_profiles() -> KeybindProfiles:
    return storage.load_profiles()


@router.put("/profiles", response_model=KeybindProfiles)
def put_profiles(body: KeybindProfiles) -> KeybindProfiles:
    try:
        return storage.save_profiles(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=KeybindProfile)
def get_keybinds() -> KeybindProfile:
    return storage.load()


@router.post("", response_model=KeybindProfile)
def save_keybinds(body: KeybindProfile) -> KeybindProfile:
    return storage.save(body)
