from __future__ import annotations

import asyncio
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


def _read_image_size(path: Path) -> tuple[int, int] | None:
    """Return (width, height) by reading only the image header — avoids full pixel decode."""
    try:
        from PIL import Image as _PIL
        with _PIL.open(path) as im:
            return im.size  # (width, height)
    except Exception:
        return None


def _run_export_blocking(export_id: str) -> None:
    """Synchronous export implementation — runs in a worker thread via asyncio.to_thread."""
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

        # Eagerly populate annotation_store from disk for frames that have
        # saved .txt labels but were not yet viewed in this session.
        # This ensures frames annotated in previous sessions are included.
        labels_dir = session.output_path / "labels"
        if labels_dir.exists():
            from app.api.routes.annotations import _load_frame_from_txt
            stem_to_idx: dict[str, int] = {p.stem: i for i, p in enumerate(frame_paths)}
            for txt_path in sorted(labels_dir.glob("*.txt")):
                frame_idx = stem_to_idx.get(txt_path.stem)
                if frame_idx is None or frame_idx in _state.annotation_store:
                    continue
                dims = frame_dims.get(frame_idx)
                if dims is None:
                    # PIL reads only the image header — much faster than cv2.imread for dims.
                    size = _read_image_size(frame_paths[frame_idx])
                    if size is None:
                        continue
                    dims = size  # already (width, height)
                    _state.frame_dims[frame_idx] = dims
                _load_frame_from_txt(
                    frame_idx, frame_paths[frame_idx], dims[0], dims[1], session.output_path
                )

        # Collect annotated frames and deduplicate export names
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
        # source_image_map: export_name → original source path (no staging copy needed)
        source_image_map: dict[str, Path] = {}

        for frame_idx, path, export_name, ann_list in frame_entries:
            dims = frame_dims.get(frame_idx)
            if dims is None:
                size = _read_image_size(path)
                if size is None:
                    continue
                dims = size
                _state.frame_dims[frame_idx] = dims

            img_w, img_h = dims
            source_image_map[export_name] = path
            coco_images.append({
                "id": frame_idx,
                "file_name": export_name,
                "width": img_w,
                "height": img_h,
            })
            for ann in ann_list:
                cat_id = ann.category_id
                if cat_id < 0 or cat_id >= len(classes):
                    continue
                x, y, w, h = ann.bbox
                ann_entry = {
                    "id": ann_id,
                    "image_id": frame_idx,
                    "category_id": cat_id,
                    "bbox": [float(x), float(y), float(w), float(h)],
                    "area": float(max(w, 0) * max(h, 0)),
                    "iscrowd": 0,
                    "segmentation": [],
                    "source": getattr(ann, "source", "manual"),
                }
                if getattr(ann, "track_id", None) is not None:
                    ann_entry["track_id"] = int(ann.track_id)
                if getattr(ann, "obb", None) is not None:
                    ann_entry["obb"] = ann.obb.model_dump(exclude_none=True)
                coco_annotations.append(ann_entry)
                ann_id += 1

        payload = {
            "images": coco_images,
            "annotations": coco_annotations,
            "categories": categories,
        }

        total = len(coco_images)
        out = job.output_path
        sorted_export_names = sorted(img["file_name"] for img in coco_images)
        export_to_original = {ename: path.name for _, path, ename, _ in frame_entries}

        if "yolo" in job.formats:
            def _on_yolo_progress(done: int, _total: int) -> None:
                job.progress = done / max(total, 1)
                if 0 < done <= len(sorted_export_names):
                    current = sorted_export_names[done - 1]
                    job.current_file = export_to_original.get(current, current)

            if session.mode == "obb":
                from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset

                export_yolo_obb_dataset(
                    payload,
                    output_dir=out,
                    source_images_dir=None,
                    split_ratios=job.split_ratios if job.use_split else None,
                    source_image_map=source_image_map,
                    on_progress=_on_yolo_progress,
                )
            elif job.use_split:
                export_yolo_dataset(
                    payload,
                    source_images_dir=None,
                    dataset_root=out,
                    split_ratios=job.split_ratios,
                    on_progress=_on_yolo_progress,
                    source_image_map=source_image_map,
                )
            else:
                export_yolo_no_split(
                    payload,
                    source_images_dir=None,
                    dataset_root=out,
                    on_progress=_on_yolo_progress,
                    source_image_map=source_image_map,
                )

        if "coco" in job.formats:
            from app.annotation.infrastructure.export.coco_exporter import export_detection_coco_json
            from app.annotation.core.export.split_service import assign_splits, normalize_split_ratios

            if job.use_split:
                ratios = normalize_split_ratios(job.split_ratios)
                assignments = assign_splits(coco_images, ratios)
                imgs_by_split: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
                for img in coco_images:
                    imgs_by_split[assignments.get(img["id"], "train")].append(img)

                running = [0]
                for split_name in ("train", "val", "test"):
                    split_imgs = imgs_by_split[split_name]
                    if not split_imgs:
                        continue
                    split_img_ids = {img["id"] for img in split_imgs}
                    split_anns = [ann for ann in coco_annotations if ann["image_id"] in split_img_ids]
                    split_payload = {"images": split_imgs, "annotations": split_anns, "categories": categories}
                    split_out = out / split_name / "annotations.json"
                    offset = running[0]
                    names_snapshot = [img["file_name"] for img in split_imgs]

                    def _on_coco_split_progress(
                        done: int, _total: int,
                        _offset: int = offset,
                        _names: list = names_snapshot,
                    ) -> None:
                        job.progress = (_offset + done) / max(total, 1)
                        if 0 < done <= len(_names):
                            job.current_file = _names[done - 1]

                    export_detection_coco_json(
                        split_payload,
                        output_path=split_out,
                        source_images_dir=None,
                        source_image_map=source_image_map,
                        on_progress=_on_coco_split_progress,
                    )
                    running[0] += len(split_imgs)
            else:
                out_json = out / "annotations.json"
                img_names = [img["file_name"] for img in coco_images]

                def _on_coco_progress(done: int, _total: int) -> None:
                    job.progress = done / max(total, 1)
                    if 0 < done <= len(img_names):
                        job.current_file = img_names[done - 1]

                export_detection_coco_json(
                    payload,
                    output_path=out_json,
                    source_images_dir=None,
                    source_image_map=source_image_map,
                    on_progress=_on_coco_progress,
                )

        job.progress = 1.0
        job.current_file = ""
        job.status = "done"

    except Exception as exc:
        job.status = "error"
        job.current_file = str(exc)


async def _run_export(export_id: str) -> None:
    """Delegate blocking file I/O to a worker thread so the event loop stays responsive."""
    await asyncio.to_thread(_run_export_blocking, export_id)


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
