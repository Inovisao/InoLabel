"""Rotas HTTP de navegação entre frames."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.frames import service
from app.api.frames.schemas import FrameResponse

router = APIRouter(prefix="/api/frames", tags=["frames"])


@router.get("/init")
def init_frames() -> dict:
    return service.init_frames()


@router.get("/list")
def list_frames(offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500),
               query: str = Query(default="", max_length=200)) -> dict:
    return service.list_frames(offset, limit, query)


@router.get("/{index}/thumbnail")
def frame_thumbnail(index: int) -> Response:
    content = service.thumbnail(index)
    return Response(content=content, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/current", response_model=FrameResponse)
def current_frame() -> FrameResponse:
    return service.current_frame()


@router.post("/next", response_model=FrameResponse)
def next_frame() -> FrameResponse:
    return service.next_frame()


@router.post("/prev", response_model=FrameResponse)
def prev_frame() -> FrameResponse:
    return service.prev_frame()


@router.post("/goto/{index}", response_model=FrameResponse)
def goto_frame(index: int) -> FrameResponse:
    return service.goto_frame(index)
