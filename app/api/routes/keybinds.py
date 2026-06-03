from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from filelock import FileLock

from app.api.schemas import KeybindProfile
from app.config import LOCAL_DIR

router = APIRouter(prefix="/api/keybinds", tags=["keybinds"])

KEYBINDS_PATH = LOCAL_DIR / "keybinds.json"
DEFAULT_KEYBINDS = KeybindProfile(profile="arrows", binds={"validate": "Return", "next": "Right", "prev": "Left"})


@router.get("", response_model=KeybindProfile)
def get_keybinds() -> KeybindProfile:
    if not KEYBINDS_PATH.exists():
        return DEFAULT_KEYBINDS
    with FileLock(str(KEYBINDS_PATH) + ".lock"):
        return KeybindProfile.model_validate(json.loads(KEYBINDS_PATH.read_text(encoding="utf-8")))


@router.post("", response_model=KeybindProfile)
def save_keybinds(body: KeybindProfile) -> KeybindProfile:
    # Coexistence: keybinds are shared by Tkinter and WebUI, so writes are
    # guarded by a file lock instead of process-local state.
    KEYBINDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(KEYBINDS_PATH) + ".lock"):
        KEYBINDS_PATH.write_text(body.model_dump_json(indent=2), encoding="utf-8")
    return body
