"""Local startup cache for user-selected paths.

The cache intentionally lives under `.local/`, which is ignored by git.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from app.config import BASE_DIR
from app.core.session import AnnotationTaskMode

CACHE_DIR = BASE_DIR / ".local"
CACHE_PATH = CACHE_DIR / "startup_cache.json"


@dataclass(frozen=True)
class StartupCache:
    data_root: Optional[Path] = None
    weights_paths: Tuple[Path, ...] = ()
    mode: Optional[AnnotationTaskMode] = None

    @property
    def weights_path(self) -> Optional[Path]:
        """Primeiro modelo — mantido para compatibilidade."""
        return self.weights_paths[0] if self.weights_paths else None


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

    # Suporta formato antigo (weights_path string) e novo (weights_paths lista)
    raw_paths = data.get("weights_paths") or []
    if not raw_paths and data.get("weights_path"):
        raw_paths = [data["weights_path"]]
    weights_paths = tuple(p for p in (_optional_path(r) for r in raw_paths) if p is not None)

    return StartupCache(
        data_root=_optional_path(data.get("data_root")),
        weights_paths=weights_paths,
        mode=mode,
    )


def save_startup_cache(
    *,
    data_root: Path,
    weights_paths: Tuple[Path, ...] = (),
    weights_path: Optional[Path] = None,
    mode: AnnotationTaskMode,
    path: Path = CACHE_PATH,
):
    """Persist startup choices locally."""

    if not weights_paths and weights_path is not None:
        weights_paths = (weights_path,)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "data_root": str(Path(data_root).expanduser()),
        "weights_paths": [str(Path(p).expanduser()) for p in weights_paths],
        "mode": mode.value,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _optional_path(value) -> Optional[Path]:
    if not value:
        return None
    return Path(str(value)).expanduser()
