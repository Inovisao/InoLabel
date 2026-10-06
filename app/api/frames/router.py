"""Rotas HTTP de navegação entre frames."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.frames import service
from app.api.frames.schemas import FrameResponse

router = APIRouter(prefix="/api/frames", tags=["frames"])


@router.get("/init")
def init_frames() -> dict:
    return service.init_frames()


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
