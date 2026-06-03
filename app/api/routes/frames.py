from __future__ import annotations

import base64
from pathlib import Path
from typing import List

import cv2
from fastapi import APIRouter, HTTPException

from app.api.schemas import Annotation, FrameResponse
from app.api.state import active_session
from app.config import IMAGE_EXTENSIONS

router = APIRouter(prefix="/api/frames", tags=["frames"])

_IMAGE_EXTS = set(IMAGE_EXTENSIONS)

# Lightweight frame state (index, cached paths)
_frame_paths: List[Path] = []
_current_index: int = 0


def _load_frame_paths() -> None:
    global _frame_paths
    session = active_session()
    if session is None:
        _frame_paths = []
        return
    root = session.data_path
    if root.is_dir():
        _frame_paths = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in _IMAGE_EXTS)
    elif root.is_file() and root.suffix.lower() in _IMAGE_EXTS:
        _frame_paths = [root]
    else:
        _frame_paths = []


def _encode_frame(path: Path) -> str:
    img = cv2.imread(str(path))
    if img is None:
        raise HTTPException(status_code=404, detail=f"Cannot read {path.name}")
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode()


@router.get("/init")
def init_frames() -> dict:
    _load_frame_paths()
    global _current_index
    _current_index = 0
    return {"total": len(_frame_paths)}


@router.get("/current", response_model=FrameResponse)
def current_frame() -> FrameResponse:
    if not _frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded. Call /frames/init first.")
    path = _frame_paths[_current_index]
    return FrameResponse(
        index=_current_index,
        total=len(_frame_paths),
        image_b64=_encode_frame(path),
        filename=path.name,
        annotations=[],
    )


@router.post("/next", response_model=FrameResponse)
def next_frame() -> FrameResponse:
    global _current_index
    if not _frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded.")
    _current_index = min(_current_index + 1, len(_frame_paths) - 1)
    return current_frame()


@router.post("/prev", response_model=FrameResponse)
def prev_frame() -> FrameResponse:
    global _current_index
    if not _frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded.")
    _current_index = max(_current_index - 1, 0)
    return current_frame()


@router.post("/goto/{index}", response_model=FrameResponse)
def goto_frame(index: int) -> FrameResponse:
    global _current_index
    if not _frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded.")
    if index < 0 or index >= len(_frame_paths):
        raise HTTPException(status_code=400, detail="Index out of range.")
    _current_index = index
    return current_frame()
