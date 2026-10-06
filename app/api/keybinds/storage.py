"""Atalhos de teclado salvos em LOCAL_DIR/keybinds.json (com o formato do app 1.0 aceito)."""

from __future__ import annotations

import json
from pathlib import Path

from filelock import FileLock
from pydantic import ValidationError

from app.api.keybinds.schemas import KeybindProfile, KeybindProfiles
from app.config import LOCAL_DIR

KEYBINDS_PATH = LOCAL_DIR / "keybinds.json"
DEFAULT_KEYBINDS = KeybindProfile(profile="arrows", binds={"validate": "Return", "next": "Right", "prev": "Left"})

DEFAULT_PROFILE = {
    "next_frame": ["ArrowRight", "D"], "prev_frame": ["ArrowLeft", "A"],
    "tool_box": ["B"], "tool_select": ["V"], "mark_negative": ["N"],
    "delete_annotation": ["Delete", "Backspace"], "deselect": ["Escape"],
    "rotate_left": ["Q"], "rotate_right": ["E"],
    "kp_skip": ["X"], "kp_visibility": ["C"], "kp_finish": ["F"],
    "kp_undo": ["Backspace"], "kp_cancel": ["Escape"],
    "classification_skip": ["Space"], "search_class": ["Slash"],
    "save": ["Ctrl+S"], "export": ["Ctrl+E"],
    "settings": ["Ctrl+Comma"], "undo": ["Ctrl+Z"],
}
DEFAULT_PROFILES = KeybindProfiles(active_profile="Padrão", profiles={"Padrão": DEFAULT_PROFILE})
_ALIASES = {"next": "next_frame", "prev": "prev_frame"}
_KEY_ALIASES = {"Right": "ArrowRight", "Left": "ArrowLeft", "Return": "Enter", "space": "Space", " ": "Space"}


def _normalize_key(value: str) -> str:
    parts = value.split("-")
    modifiers = {"Control": "Ctrl", "Command": "Ctrl", "Meta": "Ctrl", "Option": "Alt"}
    if len(parts) > 1 and all(part in {"Control", "Ctrl", "Command", "Meta", "Option", "Alt", "Shift"} for part in parts[:-1]):
        prefix = "+".join(modifiers.get(part, part) for part in parts[:-1]) + "+"
        return prefix + _normalize_key(parts[-1])
    return _KEY_ALIASES.get(value, value.upper() if len(value) == 1 else value)
_CONTEXT = {
    "next_frame": "all", "prev_frame": "all", "tool_box": "edit", "tool_select": "edit",
    "mark_negative": "edit", "delete_annotation": "edit", "deselect": "edit",
    "rotate_left": "obb", "rotate_right": "obb", "kp_skip": "kp", "kp_visibility": "kp",
    "kp_finish": "kp", "kp_undo": "kp", "kp_cancel": "kp",
    "classification_skip": "classification", "search_class": "all", "save": "all",
    "export": "all", "settings": "all", "undo": "all",
}


def _overlap(a: str, b: str) -> bool:
    contexts = {_CONTEXT[a], _CONTEXT[b]}
    return "all" in contexts or len(contexts) == 1 or "edit" in contexts and ("obb" in contexts or "kp" in contexts)


def _same_shortcut(a: str, b: str) -> bool:
    return a.replace("Shift+", "") == b.replace("Shift+", "")


def _profiles_from_data(data: object) -> KeybindProfiles | None:
    if not isinstance(data, dict):
        return None
    if "profiles" in data:
        raw = data.get("profiles")
        active = data.get("active_profile")
    elif "binds" in data:
        active = data.get("profile")
        raw = {active: data.get("binds")}
    else:
        return None
    if not isinstance(active, str) or not isinstance(raw, dict) or active not in raw:
        return None
    profiles = {"Padrão": {k: list(v) for k, v in DEFAULT_PROFILE.items()}}
    for name, binds in raw.items():
        if not isinstance(name, str) or not isinstance(binds, dict):
            continue
        normalized = {k: list(v) for k, v in DEFAULT_PROFILE.items()}
        for key, value in binds.items():
            action = _ALIASES.get(key, key)
            if action not in DEFAULT_PROFILE:
                continue
            keys = value if isinstance(value, list) else [value]
            normalized[action] = [_normalize_key(v) for v in keys if isinstance(v, str) and v]
        if name != "Padrão":
            profiles[name] = normalized
    return KeybindProfiles(active_profile=active if active in profiles else "Padrão", profiles=profiles)


def load_profiles() -> KeybindProfiles:
    if not KEYBINDS_PATH.exists():
        return DEFAULT_PROFILES.model_copy(deep=True)
    with FileLock(str(KEYBINDS_PATH) + ".lock"):
        try:
            return _profiles_from_data(json.loads(KEYBINDS_PATH.read_text(encoding="utf-8"))) or DEFAULT_PROFILES.model_copy(deep=True)
        except (OSError, ValueError):
            return DEFAULT_PROFILES.model_copy(deep=True)


def save_profiles(body: KeybindProfiles) -> KeybindProfiles:
    if body.active_profile not in body.profiles:
        raise ValueError("O perfil ativo não existe.")
    if body.profiles.get("Padrão") != DEFAULT_PROFILE or any(not name.strip() or name != name.strip() for name in body.profiles):
        raise ValueError("O perfil padrão não pode ser alterado e os nomes devem ser preenchidos.")
    for name, binds in body.profiles.items():
        if set(binds) != set(DEFAULT_PROFILE):
            raise ValueError(f"Ações inválidas ou ausentes no perfil {name}.")
        used: dict[str, str] = {}
        for action, keys in binds.items():
            if not keys or len(keys) > 2 or any(not key.strip() or key != key.strip() for key in keys) or len(set(keys)) != len(keys) or len(keys) == 2 and _same_shortcut(*keys):
                raise ValueError(f"Teclas inválidas para {action} no perfil {name}.")
            for key in keys:
                if _CONTEXT[action] in {"all", "classification"} and (key in "0123456789" or key in {"Enter", "Backspace", "Escape"}):
                    raise ValueError(f"A tecla {key} é reservada para digitar classes na classificação.")
                other = next((previous for previous_key, previous in used.items() if _same_shortcut(previous_key, key)), None)
                allowed = {action, other} in ({"kp_cancel", "deselect"}, {"kp_undo", "delete_annotation"})
                if other and _overlap(action, other) and not allowed:
                    raise ValueError(f"A tecla {key} está atribuída a {other} e {action} no perfil {name}.")
                used[key] = action
    KEYBINDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(KEYBINDS_PATH) + ".lock"):
        if KEYBINDS_PATH.exists() and _read_keybinds()[1] and not _legacy_backup_path().exists():
            _legacy_backup_path().write_bytes(KEYBINDS_PATH.read_bytes())
        KEYBINDS_PATH.write_text(body.model_dump_json(indent=2), encoding="utf-8")
    return body


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
    return KeybindProfile(profile=name, binds={str(k): str(v[0] if isinstance(v, list) else v) for k, v in binds.items() if v})


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
        is_tkinter = isinstance(data, dict) and isinstance(data.get("profiles"), dict) and not any(
            isinstance(value, list) for binds in data["profiles"].values() if isinstance(binds, dict) for value in binds.values()
        )
        return (legacy, is_tkinter) if legacy is not None else (DEFAULT_KEYBINDS, False)


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
