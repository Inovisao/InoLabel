"""Local model configuration, labeling jobs, and explicit proposal review."""

from typing import Optional

from fastapi import APIRouter, Query

from app.core.model_runtime import runtime_info
from app.autolabeling import service
from app.autolabeling.adapters.registry import capabilities as adapter_capabilities
from app.autolabeling.models import ModelConfig, ReviewRequest, RunRequest

router = APIRouter(prefix='/api/autolabeling', tags=['autolabeling'])


@router.get('/runtime')
def runtime():
    return runtime_info()


@router.get('/capabilities')
def capabilities():
    return adapter_capabilities()


@router.get('/config')
def configuration():
    return service.configuration()


@router.put('/config')
def save_configuration(body: ModelConfig):
    return service.save_configuration(body)


@router.post('/models/inspect')
def inspect_model(body: ModelConfig):
    return service.inspect_model(body)


@router.get('/runs')
def runs():
    return service.runs()


@router.post('/runs')
def create_run(body: RunRequest):
    return service.create_run(body)


@router.get('/runs/{run_id}/proposals')
def proposals(run_id: str, frame_index: Optional[int] = Query(default=None, ge=0),
              offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)):
    return service.proposals(run_id, frame_index, offset, limit)


@router.post('/runs/{run_id}/cancel')
def cancel(run_id: str):
    return service.stop_run(run_id)


@router.post('/runs/{run_id}/resume')
def resume(run_id: str):
    return service.resume_run(run_id)


@router.post('/runs/{run_id}/accept')
def accept(run_id: str, body: ReviewRequest):
    return service.review(run_id, body, 'accept')


@router.post('/runs/{run_id}/reject')
def reject(run_id: str, body: ReviewRequest):
    return service.review(run_id, body, 'reject')


@router.post('/runs/{run_id}/undo')
def undo(run_id: str, body: ReviewRequest):
    return service.review(run_id, body, 'undo')
