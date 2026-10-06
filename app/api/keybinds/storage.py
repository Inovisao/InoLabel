"""Atalhos de teclado salvos em LOCAL_DIR/keybinds.json (com o formato do app 1.0 aceito)."""

from __future__ import annotations

import json
from pathlib import Path

from filelock import FileLock
from pydantic import ValidationError

from app.api.keybinds.schemas import KeybindProfile
from app.config import LOCAL_DIR

KEYBINDS_PATH = LOCAL_DIR / "keybinds.json"
DEFAULT_KEYBINDS = KeybindProfile(profile="arrows", binds={"validate": "Return", "next": "Right", "prev": "Left"})


def _legacy_backup_path() -> Path:
    # Derivado na chamada: os testes trocam KEYBINDS_PATH.
    return KEYBINDS_PATH.with_name(KEYBINDS_PATH.stem + ".tkinter" + KEYBINDS_PATH.suffix)


def _from_legacy(data: object) -> KeybindProfile | None:
    """Converte o arquivo do app Tkinter 1.0 ({active_profile, profiles}) para o perfil ativo."""
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        return None
    name = str(data.get("active_profile") or "")
    binds = data["profiles"].get(name)
    if not isinstance(binds, dict):
        return None
    return KeybindProfile(profile=name, binds={str(k): str(v) for k, v in binds.items() if v})


def _read_keybinds() -> tuple[KeybindProfile, bool]:
    """Retorna (perfil, arquivo_esta_no_formato_antigo). Arquivo ilegivel cai no padrao."""
    try:
        data = json.loads(KEYBINDS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_KEYBINDS, False
    try:
        return KeybindProfile.model_validate(data), False
    except ValidationError:
        legacy = _from_legacy(data)
        return (legacy, True) if legacy is not None else (DEFAULT_KEYBINDS, False)


def load() -> KeybindProfile:
    """Perfil salvo (o do app Tkinter 1.0 é convertido), ou o padrão."""
    if not KEYBINDS_PATH.exists():
        return DEFAULT_KEYBINDS
    with FileLock(str(KEYBINDS_PATH) + ".lock"):
        return _read_keybinds()[0]


def save(body: KeybindProfile) -> KeybindProfile:
    KEYBINDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(KEYBINDS_PATH) + ".lock"):
        # O arquivo do app Tkinter 1.0 tem outro formato (varios perfis). Antes de
        # sobrescreve-lo, guarda uma copia para nao perder os atalhos do usuario.
        if KEYBINDS_PATH.exists() and _read_keybinds()[1] and not _legacy_backup_path().exists():
            _legacy_backup_path().write_bytes(KEYBINDS_PATH.read_bytes())
        KEYBINDS_PATH.write_text(body.model_dump_json(indent=2), encoding="utf-8")
    return body
