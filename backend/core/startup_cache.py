"""Cache de inicializacao do usuario — persiste entre sessoes no diretorio home."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

# Cache em ~/.inolabel/ para sobreviver a atualizacoes do bundle e reinstalacoes
CACHE_DIR = Path.home() / ".inolabel"
CACHE_PATH = CACHE_DIR / "startup_cache.json"


def load_startup_cache(path: Path = CACHE_PATH) -> Dict[str, Any]:
    """Carrega o cache como dicionario generico. Retorna {} se ausente ou invalido."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # pylint: disable=broad-except
        return {}


def save_startup_cache(data: Dict[str, Any], path: Path = CACHE_PATH) -> None:
    """Persiste o cache como dicionario JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
