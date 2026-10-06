"""Exportação do dataset: cria o job, roda em segundo plano e informa o progresso."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.api import state as _state
from app.api.common.errors import InvalidInput, NotFound
from app.api.export import augmentation, payload, writers
from app.api.export.schemas import ExportProgressResponse, ExportRequest
from app.core.export_package import verify_dataset_links, zip_dataset
from app.core.exporter import ExportJob, normalize_split


def safe_output_path(destination: str, name: str) -> Path:
    """<destino>/<nome>, recusando nomes que saiam do destino (ex.: "../x")."""
    dest = Path(destination).expanduser().resolve()
    out = (dest / name).resolve()
    try:
        out.relative_to(dest)
    except ValueError:
        raise ValueError(f"Nome do dataset inválido: '{name}' sai do diretório de destino.")
    return out


def create_job(body: ExportRequest) -> ExportJob:
    if _state.get_session(body.session_id) is None:
        raise NotFound("Sessão não encontrada")
    try:
        split = normalize_split(body.split.model_dump())
        output_path = safe_output_path(body.destination, body.name)
    except ValueError as exc:
        raise InvalidInput(str(exc)) from exc
    return _state.create_export(
        ExportJob(
            destination=output_path.parent,
            name=output_path.name,
            formats=body.formats,
            use_split=body.use_split,
            split_ratios=(split["train"], split["val"], split["test"]),
            zip_output=body.zip,
            augmentation=augmentation.preset_for(body),
            coco_layout=body.coco_layout,
        )
    )


def progress(export_id: str) -> ExportProgressResponse:
    job = _state.get_export(export_id)
    if job is None:
        raise NotFound("Exportação não encontrada")
    return ExportProgressResponse(
        export_id=job.export_id,
        progress=job.progress,
        current_file=job.current_file,
        status=job.status,
        output_path=str(job.output_path),
        zip_path=str(job.zip_path) if job.zip_path is not None else None,
    )


async def run_export(export_id: str) -> None:
    """Roda a exportação numa thread: o I/O de arquivos não trava o servidor."""
    await asyncio.to_thread(run_export_blocking, export_id)


def run_export_blocking(export_id: str) -> None:
    job = _state.get_export(export_id)
    if job is None:
        return
    session = _state.active_session()
    if session is None:
        job.status = "error"
        job.current_file = "Nenhuma sessão ativa."
        return
    try:
        data = payload.collect(session)
        if data.images:
            if "yolo" in job.formats:
                writers.write_yolo(job, session, data)
            if "coco" in job.formats:
                writers.write_coco(job, data)
            if job.zip_output:
                _package(job)
        job.progress = 1.0
        job.current_file = ""
        job.status = "done"
    except Exception as exc:
        job.status = "error"
        job.current_file = str(exc)


def _package(job: ExportJob) -> None:
    """Gera o .zip. Nada vai para o pacote sem as referências conferidas: imagem com o
    seu label, file_name do COCO com a imagem ao lado."""
    job.current_file = "Conferindo referências..."
    verify_dataset_links(job.output_path)

    def on_zip_progress(done: int, total: int, name: str) -> None:
        job.progress = done / max(total, 1)
        job.current_file = f"Compactando: {name}"

    job.progress = 0.0
    job.zip_path = zip_dataset(job.output_path, on_progress=on_zip_progress)
