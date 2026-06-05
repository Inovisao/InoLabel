from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import ExportProgressResponse, ExportRequest, ExportStartResponse
from app.api.state import create_export, get_export, get_session

router = APIRouter(prefix="/api/export", tags=["export"])


async def _run_export(export_id: str) -> None:
    from app.api import state as _state
    from app.api.state import active_session
    import cv2

    job = get_export(export_id)
    if job is None:
        return

    session = active_session()
    if session is None:
        job.status = "error"
        job.current_file = "Nenhuma sessão ativa."
        return

    try:
        out = job.output_path
        imgs_dir = out / "images"
        labels_dir = out / "labels"
        imgs_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

        classes = session.classes
        (out / "classes.txt").write_text("\n".join(classes))

        yaml_lines = [
            f"path: {out}",
            "train: images",
            "val: images",
            f"nc: {len(classes)}",
            f"names: {classes}",
        ]
        (out / "data.yaml").write_text("\n".join(yaml_lines) + "\n")

        frame_paths = _state.frame_paths
        frame_dims = _state.frame_dims
        total = len([v for v in _state.annotation_store.values() if v])
        done = 0

        for idx, ann_list in _state.annotation_store.items():
            if not ann_list or idx >= len(frame_paths):
                continue
            path = frame_paths[idx]
            job.current_file = path.name

            dims = frame_dims.get(idx)
            if dims is None:
                img = cv2.imread(str(path))
                if img is None:
                    continue
                h, w = img.shape[:2]
                dims = (w, h)

            img_w, img_h = dims
            shutil.copy2(path, imgs_dir / path.name)

            txt_path = labels_dir / (path.stem + ".txt")
            with open(txt_path, "w") as f:
                for ann in ann_list:
                    x, y, w, h = ann.bbox
                    cx = (x + w / 2) / img_w
                    cy = (y + h / 2) / img_h
                    wn = w / img_w
                    hn = h / img_h
                    f.write(f"{ann.category_id} {cx:.6f} {cy:.6f} {wn:.6f} {hn:.6f}\n")

            done += 1
            job.progress = done / max(total, 1)

        job.progress = 1.0
        job.current_file = ""
        job.status = "done"

    except Exception as exc:
        job.status = "error"
        job.current_file = str(exc)


@router.post("", response_model=ExportStartResponse)
async def start_export(body: ExportRequest, background_tasks: BackgroundTasks) -> ExportStartResponse:
    from app.core.exporter import ExportJob, normalize_split

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
