from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from backend.config import BASE_DIR
from backend.annotation.keybinds.actions import ACTION_REGISTRY
from backend.annotation.keybinds.keybind_map import KeybindMap

KEYBINDS_PATH = BASE_DIR / ".local" / "keybinds.json"

_BUILTIN_PROFILES = {"arrows", "wasd"}


class KeybindRepository:
    def __init__(self, path: Path = KEYBINDS_PATH):
        self._path = path

    # ── defaults ─────────────────────────────────────────────────────────────

    def get_defaults(self) -> Dict[str, KeybindMap]:
        arrows: Dict[str, str] = {}
        wasd: Dict[str, str] = {}
        for action in ACTION_REGISTRY:
            arrows[action.id] = action.default_arrows
            wasd[action.id] = action.default_wasd
        return {
            "arrows": KeybindMap(name="arrows", bindings=arrows),
            "wasd": KeybindMap(name="wasd", bindings=wasd),
        }

    # ── load / save ───────────────────────────────────────────────────────────

    def load(self) -> Tuple[str, Dict[str, KeybindMap]]:
        """Retorna (profile_ativo, {nome: KeybindMap})."""
        defaults = self.get_defaults()
        if not self._path.exists():
            return "arrows", defaults

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:  # pylint: disable=broad-except
            return "arrows", defaults

        profiles: Dict[str, KeybindMap] = dict(defaults)

        raw_profiles = data.get("profiles", {})
        if isinstance(raw_profiles, dict):
            for name, bindings in raw_profiles.items():
                if isinstance(bindings, dict):
                    merged = dict(defaults.get(name, defaults["arrows"]).bindings)
                    merged.update({k: v for k, v in bindings.items() if isinstance(k, str) and isinstance(v, str)})
                    profiles[name] = KeybindMap(name=name, bindings=merged)

        active = data.get("active_profile", "arrows")
        if active not in profiles:
            active = "arrows"

        return active, profiles

    def save(self, active: str, profiles: Dict[str, KeybindMap]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "active_profile": active,
            "profiles": {name: km.to_dict() for name, km in profiles.items()},
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def is_builtin(name: str) -> bool:
        return name in _BUILTIN_PROFILES
