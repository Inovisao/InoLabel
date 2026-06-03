from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import ExportProgressResponse, ExportRequest, ExportStartResponse
from app.api.state import create_export, get_export, get_session
from app.core.exporter import ExportJob, normalize_split

router = APIRouter(prefix="/api/export", tags=["export"])


async def _run_export(export_id: str) -> None:
    job = get_export(export_id)
    if job is None:
        return
    # Coexistence: real dataset export can later call app.core exporters here;
    # the API request thread only tracks progress and never blocks on UI code.
    job.output_path.mkdir(parents=True, exist_ok=True)
    job.progress = 1.0
    job.status = "done"


@router.post("", response_model=ExportStartResponse)
async def start_export(body: ExportRequest, background_tasks: BackgroundTasks) -> ExportStartResponse:
    session = get_session(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    try:
        normalize_split(body.split.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job = create_export(
        ExportJob(
            destination=Path(body.destination).expanduser(),
            name=body.name,
            formats=body.formats,
        )
    )
    background_tasks.add_task(_run_export, job.export_id)
    return ExportStartResponse(export_id=job.export_id)


@router.get("/{export_id}/progress", response_model=ExportProgressResponse)
def export_progress(export_id: str) -> ExportProgressResponse:
    job = get_export(export_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Exportação não encontrada")
    return ExportProgressResponse(
        export_id=job.export_id,
        progress=job.progress,
        current_file=job.current_file,
        status=job.status,
    )
