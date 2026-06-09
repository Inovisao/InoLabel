from __future__ import annotations

import base64
from pathlib import Path

import cv2
from fastapi import APIRouter, HTTPException

from app.api import state as _state
from app.api.schemas import FrameResponse
from app.config import IMAGE_EXTENSIONS

router = APIRouter(prefix="/api/frames", tags=["frames"])

_IMAGE_EXTS = set(IMAGE_EXTENSIONS)
_current_index: int = 0
_loaded_from_disk: set[int] = set()


def _load_frame_paths() -> None:
    session = _state.active_session()
    if session is None:
        _state.frame_paths.clear()
        return
    root = session.data_path
    if root.is_dir():
        _state.frame_paths[:] = sorted(
            p for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
        )
    elif root.is_file() and root.suffix.lower() in _IMAGE_EXTS:
        _state.frame_paths[:] = [root]
    else:
        _state.frame_paths.clear()


def _encode_and_store_dims(path: Path, index: int) -> str:
    img = cv2.imread(str(path))
    if img is None:
        raise HTTPException(status_code=404, detail=f"Cannot read {path.name}")
    h, w = img.shape[:2]
    _state.frame_dims[index] = (w, h)
    _lazy_load_from_disk(index, path, w, h)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode()


def _lazy_load_from_disk(index: int, path: Path, img_w: int, img_h: int) -> None:
    """First time a frame is seen: load saved annotations from disk into memory."""
    if index in _loaded_from_disk:
        return
    _loaded_from_disk.add(index)
    session = _state.active_session()
    if session is None:
        return
    if index not in _state.annotation_store:
        # Import here to avoid top-level circular dependency
        from app.api.routes.annotations import _load_frame_from_txt
        _load_frame_from_txt(index, path, img_w, img_h, session.output_path)


def _make_response(index: int) -> FrameResponse:
    """Build FrameResponse reading annotations directly from shared state."""
    path = _state.frame_paths[index]
    image_b64 = _encode_and_store_dims(path, index)

    # Read annotations from the SAME state object that annotations.py writes to
    anns = _state.annotation_store.get(index, [])
    has_anns = bool(anns)

    return FrameResponse(
        index=index,
        total=len(_state.frame_paths),
        image_b64=image_b64,
        filename=path.name,
        annotations=list(anns),   # copy to avoid Pydantic mutating shared list
        is_saved=has_anns,
    )


@router.get("/init")
def init_frames() -> dict:
    global _current_index
    _load_frame_paths()
    _current_index = 0
    _loaded_from_disk.clear()
    _state.frame_dims.clear()
    return {"total": len(_state.frame_paths)}


@router.get("/current", response_model=FrameResponse)
def current_frame() -> FrameResponse:
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded. Call /frames/init first.")
    return _make_response(_current_index)


@router.post("/next", response_model=FrameResponse)
def next_frame() -> FrameResponse:
    global _current_index
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded.")
    _current_index = min(_current_index + 1, len(_state.frame_paths) - 1)
    return _make_response(_current_index)


@router.post("/prev", response_model=FrameResponse)
def prev_frame() -> FrameResponse:
    global _current_index
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded.")
    _current_index = max(_current_index - 1, 0)
    return _make_response(_current_index)


@router.post("/goto/{index}", response_model=FrameResponse)
def goto_frame(index: int) -> FrameResponse:
    global _current_index
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded.")
    if index < 0 or index >= len(_state.frame_paths):
        raise HTTPException(status_code=400, detail="Index out of range.")
    _current_index = index
    return _make_response(_current_index)
