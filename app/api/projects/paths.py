"""Validação de caminhos escolhidos no wizard (dataset e pesos do modelo)."""

from __future__ import annotations

from pathlib import Path

from app.api.common.errors import InvalidInput
from app.config import IMAGE_EXTENSIONS, IMAGE_LIST_EXTENSIONS, VIDEO_EXTENSIONS


class InvalidPath(InvalidInput):
    """Caminho recusado; a rota responde {"valid": false, "error": ...} (formato do wizard)."""


def path_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if path.is_dir():
        return "folder"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in IMAGE_LIST_EXTENSIONS:
        return "txt"
    return "unknown"


def validate_path(raw: str) -> dict:
    path = Path(raw).expanduser()
    if not path.exists():
        raise InvalidPath("Caminho não encontrado")
    kind = path_type(path)
    if kind == "unknown":
        raise InvalidPath("Tipo de arquivo não suportado")
    file_count = 0
    if path.is_dir():
        allowed = set(IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + IMAGE_LIST_EXTENSIONS)
        file_count = sum(1 for child in path.rglob("*") if child.is_file() and child.suffix.lower() in allowed)
    else:
        file_count = 1
    return {"valid": True, "type": kind, "file_count": file_count}


def validate_model(raw: str) -> dict:
    path = Path(raw).expanduser()
    if not path.exists():
        raise InvalidPath("Arquivo não encontrado")
    if not path.is_file() or path.suffix.lower() != ".pt":
        raise InvalidPath("Informe um arquivo .pt legível")
    try:
        size_mb = round(path.stat().st_size / (1024 * 1024), 1)
    except OSError:
        raise InvalidPath("Arquivo não legível")
    return {"valid": True, "size_mb": size_mb}
