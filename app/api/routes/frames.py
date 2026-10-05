from __future__ import annotations

import base64
import os
import threading
from collections import OrderedDict
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

# LRU cache: keeps the last N decoded frames in memory so backwards navigation
# and repeated views don't re-read the same image from disk.
_FRAME_CACHE_MAX = 8
_frame_b64_cache: OrderedDict[int, str] = OrderedDict()
# Set of frame indices currently being decoded in a background thread.
_prefetching: set[int] = set()


def _load_frame_paths() -> None:
    session = _state.active_session()
    if session is None:
        _state.frame_paths.clear()
        return
    root = session.data_path
    if root.is_dir():
        # os.walk is faster than rglob("*") for large trees: it uses scandir
        # internally and avoids allocating Path objects for non-image files.
        results: list[Path] = []
        for dirpath, _dirnames, filenames in os.walk(str(root)):
            dir_p = Path(dirpath)
            for fn in filenames:
                if Path(fn).suffix.lower() in _IMAGE_EXTS:
                    results.append(dir_p / fn)
        _state.frame_paths[:] = sorted(results)
    elif root.is_file() and root.suffix.lower() in _IMAGE_EXTS:
        _state.frame_paths[:] = [root]
    else:
        _state.frame_paths.clear()


def _prefetch_frame(index: int) -> None:
    """Decode and cache a frame in a background thread — failures are silently ignored."""
    try:
        if index < 0 or not _state.frame_paths or index >= len(_state.frame_paths):
            return
        if index in _frame_b64_cache:
            return
        path = _state.frame_paths[index]
        img = cv2.imread(str(path))
        if img is None:
            return
        h, w = img.shape[:2]
        _state.frame_dims[index] = (w, h)
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64 = base64.b64encode(buf).decode()
        if index not in _frame_b64_cache:
            _frame_b64_cache[index] = b64
            if len(_frame_b64_cache) > _FRAME_CACHE_MAX:
                _frame_b64_cache.popitem(last=False)
    except Exception:
        pass
    finally:
        _prefetching.discard(index)


def _trigger_prefetch(index: int) -> None:
    """Spawn a background thread to pre-decode index if not cached or already in-flight."""
    if index < 0 or not _state.frame_paths or index >= len(_state.frame_paths):
        return
    if index in _frame_b64_cache or index in _prefetching:
        return
    _prefetching.add(index)
    threading.Thread(target=_prefetch_frame, args=(index,), daemon=True).start()


def _sync_session_frame(index: int) -> None:
    """Keep session.current_frame in sync with _current_index for persistent resume."""
    session = _state.active_session()
    if session is not None:
        session.current_frame = index


def _encode_and_store_dims(path: Path, index: int) -> str:
    if index in _frame_b64_cache:
        _frame_b64_cache.move_to_end(index)
        # Frame may have been pre-fetched without annotation loading — ensure they're loaded.
        dims = _state.frame_dims.get(index)
        if dims:
            _lazy_load_from_disk(index, path, dims[0], dims[1])
        return _frame_b64_cache[index]
    img = cv2.imread(str(path))
    if img is None:
        raise HTTPException(status_code=404, detail=f"Cannot read {path.name}")
    h, w = img.shape[:2]
    _state.frame_dims[index] = (w, h)
    _lazy_load_from_disk(index, path, w, h)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    b64 = base64.b64encode(buf).decode()
    _frame_b64_cache[index] = b64
    if len(_frame_b64_cache) > _FRAME_CACHE_MAX:
        _frame_b64_cache.popitem(last=False)
    return b64


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

    # Bidirectional pre-fetch: both neighbours so forward AND backward navigation is instant.
    _trigger_prefetch(index + 1)
    _trigger_prefetch(index - 1)

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
    session = _state.active_session()
    start = session.current_frame if session is not None else 0
    # Clamp: frame count may differ from when the session was last saved.
    _current_index = min(start, len(_state.frame_paths) - 1) if _state.frame_paths else 0
    _loaded_from_disk.clear()
    _state.frame_dims.clear()
    _frame_b64_cache.clear()
    _prefetching.clear()
    return {"total": len(_state.frame_paths), "current_index": _current_index}


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
    _sync_session_frame(_current_index)
    return _make_response(_current_index)


@router.post("/prev", response_model=FrameResponse)
def prev_frame() -> FrameResponse:
    global _current_index
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded.")
    _current_index = max(_current_index - 1, 0)
    _sync_session_frame(_current_index)
    return _make_response(_current_index)


@router.post("/goto/{index}", response_model=FrameResponse)
def goto_frame(index: int) -> FrameResponse:
    global _current_index
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded.")
    if index < 0 or index >= len(_state.frame_paths):
        raise HTTPException(status_code=400, detail="Index out of range.")
    _current_index = index
    _sync_session_frame(_current_index)
    return _make_response(_current_index)
