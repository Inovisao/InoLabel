"""Rotas HTTP da exportação."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.api.export import augmentation, service
from app.api.export.schemas import (
    AugmentationOption,
    ExportProgressResponse,
    ExportRequest,
    ExportStartResponse,
)

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/augmentations", response_model=list[AugmentationOption])
def list_augmentations() -> list[AugmentationOption]:
    return augmentation.catalog()


@router.post("", response_model=ExportStartResponse)
async def start_export(body: ExportRequest, background_tasks: BackgroundTasks) -> ExportStartResponse:
    job = service.create_job(body)
    background_tasks.add_task(service.run_export, job.export_id)
    return ExportStartResponse(export_id=job.export_id)


@router.get("/{export_id}/progress", response_model=ExportProgressResponse)
def export_progress(export_id: str) -> ExportProgressResponse:
    return service.progress(export_id)
