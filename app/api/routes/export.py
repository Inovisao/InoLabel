from __future__ import annotations

import shutil as _shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import ExportProgressResponse, ExportRequest, ExportStartResponse
from app.api.state import create_export, get_export, get_session

router = APIRouter(prefix="/api/export", tags=["export"])


def _safe_output_path(destination: str, name: str) -> Path:
    dest = Path(destination).expanduser().resolve()
    out = (dest / name).resolve()
    try:
        out.relative_to(dest)
    except ValueError:
        raise ValueError(f"Nome do dataset inválido: '{name}' sai do diretório de destino.")
    return out


async def _run_export(export_id: str) -> None:
    import cv2
    from app.api import state as _state
    from app.api.state import active_session
    from app.annotation.infrastructure.export.yolo_exporter import (
        export_yolo_dataset,
        export_yolo_no_split,
    )

    job = get_export(export_id)
    if job is None:
        return

    session = active_session()
    if session is None:
        job.status = "error"
        job.current_file = "Nenhuma sessão ativa."
        return

    try:
        classes = session.classes
        categories = [{"id": i, "name": name} for i, name in enumerate(classes)]

        frame_paths = _state.frame_paths
        frame_dims = _state.frame_dims

        # Collect annotated frames and deduplicate staged file names
        frame_entries: list[tuple[int, Path, str, list]] = []
        used_names: set[str] = set()
        for frame_idx, ann_list in _state.annotation_store.items():
            if not ann_list or frame_idx >= len(frame_paths):
                continue
            path = frame_paths[frame_idx]
            candidate = path.name
            if candidate in used_names:
                candidate = f"{path.stem}_{frame_idx}{path.suffix}"
            used_names.add(candidate)
            frame_entries.append((frame_idx, path, candidate, ann_list))

        if not frame_entries:
            job.progress = 1.0
            job.status = "done"
            return

        # Build COCO payload from in-memory annotation store
        coco_images: list[dict] = []
        coco_annotations: list[dict] = []
        ann_id = 1
        staged: dict[int, tuple[Path, str]] = {}

        for frame_idx, path, staged_name, ann_list in frame_entries:
            dims = frame_dims.get(frame_idx)
            if dims is None:
                img = cv2.imread(str(path))
                if img is None:
                    continue
                h, w = img.shape[:2]
                dims = (w, h)
                _state.frame_dims[frame_idx] = dims

            img_w, img_h = dims
            staged[frame_idx] = (path, staged_name)
            coco_images.append({
                "id": frame_idx,
                "file_name": staged_name,
                "width": img_w,
                "height": img_h,
            })
            for ann in ann_list:
                cat_id = ann.category_id
                if cat_id < 0 or cat_id >= len(classes):
                    continue
                x, y, w, h = ann.bbox
                coco_annotations.append({
                    "id": ann_id,
                    "image_id": frame_idx,
                    "category_id": cat_id,
                    "bbox": [float(x), float(y), float(w), float(h)],
                    "area": float(max(w, 0) * max(h, 0)),
                    "iscrowd": 0,
                    "segmentation": [],
                })
                ann_id += 1

        payload = {
            "images": coco_images,
            "annotations": coco_annotations,
            "categories": categories,
        }

        total = len(coco_images)
        # Build sorted name → original filename lookup to match export_yolo_dataset's sort order
        sorted_staged_names = sorted(img["file_name"] for img in coco_images)
        staged_to_original = {staged_name: path.name for _, path, staged_name, _ in frame_entries}

        def _on_progress(done: int, _total: int) -> None:
            job.progress = done / max(total, 1)
            if 0 < done <= len(sorted_staged_names):
                staged = sorted_staged_names[done - 1]
                job.current_file = staged_to_original.get(staged, staged)

        out = job.output_path
        with tempfile.TemporaryDirectory() as staging_dir:
            staging_path = Path(staging_dir)
            for _idx, (src_path, staged_name) in staged.items():
                _shutil.copy2(src_path, staging_path / staged_name)

            if job.use_split:
                export_yolo_dataset(
                    payload,
                    source_images_dir=staging_path,
                    dataset_root=out,
                    split_ratios=job.split_ratios,
                    on_progress=_on_progress,
                )
            else:
                export_yolo_no_split(
                    payload,
                    source_images_dir=staging_path,
                    dataset_root=out,
                    on_progress=_on_progress,
                )

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
        split = normalize_split(body.split.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        output_path = _safe_output_path(body.destination, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job = create_export(
        ExportJob(
            destination=output_path.parent,
            name=output_path.name,
            formats=body.formats,
            use_split=body.use_split,
            split_ratios=(split["train"], split["val"], split["test"]),
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
