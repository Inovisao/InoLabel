"""Rotas HTTP da sessão de anotação."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.api.session import service
from app.api.session.schemas import (
    SessionActionRequest,
    SessionActionResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStatusResponse,
    SessionStopResponse,
)

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest) -> SessionStartResponse:
    # Varre o dataset e lê o estado do projeto: fora da thread do servidor.
    return await run_in_threadpool(service.start_session, req)


@router.get("/status")
def active_status() -> dict:
    return service.active_status()


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
def get_status(session_id: str) -> SessionStatusResponse:
    return service.status(session_id)


@router.post("/{session_id}/action", response_model=SessionActionResponse)
def run_action(session_id: str, body: SessionActionRequest) -> SessionActionResponse:
    return service.run_action(session_id, body)


@router.post("/stop")
def stop_active_session() -> dict:
    return service.stop_active()


@router.post("/{session_id}/stop", response_model=SessionStopResponse)
def stop_session(session_id: str) -> SessionStopResponse:
    return service.stop(session_id)
