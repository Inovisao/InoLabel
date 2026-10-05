"""Caminhos montados a partir do estado (JSON) nunca podem sair da pasta esperada.

`file_name` vem do annotations.coco.json; um estado corrompido ou editado com
"../" faria uma remocao apagar arquivos fora da pasta de saida.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def contained_path(base: Path, relative: str) -> Optional[Path]:
    """`base / relative` resolvido, ou None se escapar de `base` (ou se relative for vazio/absoluto)."""
    relative = str(relative or "").strip()
    if not relative or Path(relative).is_absolute():
        return None
    base = Path(base).resolve()
    candidate = (base / relative).resolve()
    if candidate == base or base not in candidate.parents:
        return None
    return candidate
