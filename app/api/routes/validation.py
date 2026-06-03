from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas import OutputsRequest, PathValidationRequest
from app.config import IMAGE_EXTENSIONS, IMAGE_LIST_EXTENSIONS, VIDEO_EXTENSIONS

router = APIRouter(prefix="/api/session", tags=["validation"])


def _invalid(message: str) -> JSONResponse:
    return JSONResponse(status_code=422, content={"valid": False, "error": message})


def _path_type(path: Path) -> str:
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


@router.post("/validate-path")
def validate_path(body: PathValidationRequest):
    path = Path(body.path).expanduser()
    if not path.exists():
        return _invalid("Caminho não encontrado")
    kind = _path_type(path)
    if kind == "unknown":
        return _invalid("Tipo de arquivo não suportado")
    file_count = 0
    if path.is_dir():
        allowed = set(IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + IMAGE_LIST_EXTENSIONS)
        file_count = sum(1 for child in path.rglob("*") if child.is_file() and child.suffix.lower() in allowed)
    else:
        file_count = 1
    return {"valid": True, "type": kind, "file_count": file_count}


@router.post("/validate-model")
def validate_model(body: PathValidationRequest):
    path = Path(body.path).expanduser()
    if not path.exists():
        return _invalid("Arquivo não encontrado")
    if not path.is_file() or path.suffix.lower() != ".pt":
        return _invalid("Informe um arquivo .pt legível")
    try:
        size_mb = round(path.stat().st_size / (1024 * 1024), 1)
    except OSError:
        return _invalid("Arquivo não legível")
    return {"valid": True, "size_mb": size_mb}


@router.get("/outputs")
def list_outputs(output_path: str):
    root = Path(output_path).expanduser()
    if not root.exists():
        return []
    sessions = []
    for child in sorted((item for item in root.iterdir() if item.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True):
        sessions.append(
            {
                "name": child.name,
                "mode": "unknown",
                "frame_count": 0,
                "created_at": datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
        )
    return sessions


@router.post("/outputs")
def list_outputs_from_body(body: OutputsRequest):
    return list_outputs(body.output_path)
