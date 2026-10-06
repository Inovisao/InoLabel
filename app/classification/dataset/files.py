"""Utilitários de arquivo: destino sem sobrescrever."""

from __future__ import annotations

from pathlib import Path



def unique_destination_path(candidate: Path) -> Path:
    """Return a non-existing path by appending a numeric suffix when needed."""

    candidate = Path(candidate)
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        next_candidate = candidate.with_name(f"{stem}__{index:03d}{suffix}")
        if not next_candidate.exists():
            return next_candidate
        index += 1
