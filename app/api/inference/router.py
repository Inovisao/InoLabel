"""Rotas HTTP da pré-anotação por modelo."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.api.inference import service
from app.api.inference.schemas import TrackingInferenceRequest, TrackingInferenceResponse

router = APIRouter(prefix="/api/inference", tags=["inference"])


@router.post("/tracking", response_model=TrackingInferenceResponse)
async def run_tracking_inference(req: TrackingInferenceRequest) -> TrackingInferenceResponse:
    session = service.session_for_request(req.session_id)
    # Modelo + rastreador por todos os frames: fora da thread do servidor.
    return await run_in_threadpool(service.run_tracking_inference, session, req)
