"""Local startup cache for user-selected paths.

The cache intentionally lives under `.local/`, which is ignored by git.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import BASE_DIR
from app.core.session import AnnotationTaskMode

CACHE_DIR = BASE_DIR / ".local"
CACHE_PATH = CACHE_DIR / "startup_cache.json"


@dataclass(frozen=True)
class StartupCache:
    data_root: Optional[Path] = None
    weights_path: Optional[Path] = None
    mode: Optional[AnnotationTaskMode] = None


def load_startup_cache(path: Path = CACHE_PATH) -> StartupCache:
    """Load cached startup choices, ignoring malformed or missing cache files."""

    if not path.exists():
        return StartupCache()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pylint: disable=broad-except
        return StartupCache()

    mode = None
    raw_mode = data.get("mode")
    if raw_mode:
        try:
            mode = AnnotationTaskMode(raw_mode)
        except ValueError:
            mode = None

    return StartupCache(
        data_root=_optional_path(data.get("data_root")),
        weights_path=_optional_path(data.get("weights_path")),
        mode=mode,
    )


def save_startup_cache(
    *,
    data_root: Path,
    weights_path: Path,
    mode: AnnotationTaskMode,
    path: Path = CACHE_PATH,
):
    """Persist startup choices locally."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "data_root": str(Path(data_root).expanduser()),
        "weights_path": str(Path(weights_path).expanduser()),
        "mode": mode.value,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _optional_path(value) -> Optional[Path]:
    if not value:
        return None
    return Path(str(value)).expanduser()
