from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import AugmentationOption, ExportProgressResponse, ExportRequest, ExportStartResponse
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

        frame_paths = _state.frame_paths
        frame_dims = _state.frame_dims

        # Eagerly populate annotation_store from disk for frames that have
        # saved .txt labels but were not yet viewed in this session.
        # This ensures frames annotated in previous sessions are included.
        labels_dir = session.output_path / "labels"
        if labels_dir.exists():
            from app.api.routes.annotations import _load_frame_from_txt
            from app.core.label_paths import find_label_file

            # Parte de cada imagem para o seu label. O caminho inverso (do .txt para
            # "a imagem com aquele stem") atribuía o label à imagem errada quando o
            # nome se repetia em subpastas.
            ambiguous = _state.ambiguous_frame_stems()
            for frame_idx, frame_path in enumerate(frame_paths):
                if frame_idx in _state.annotation_store:
                    continue
                if find_label_file(session.output_path, frame_path, session.data_path, ambiguous) is None:
                    continue
                dims = frame_dims.get(frame_idx)
                if dims is None:
                    # PIL reads only the image header — much faster than cv2.imread for dims.
                    size = _read_image_size(frame_path)
                    if size is None:
                        continue
                    dims = size  # already (width, height)
                    _state.frame_dims[frame_idx] = dims
                _load_frame_from_txt(
                    frame_idx, frame_path, dims[0], dims[1], session.output_path
                )

        # Mesmo payload do annotations.coco.json do projeto: categorias a partir de 1,
        # file_name relativo ao dataset (preserva subpastas) e negativos marcados.
        from app.api.routes.annotations import _frame_dims
        from app.core.coco_state import build_payload, relative_name

        for idx in set(_state.annotation_store) | _state.reviewed_frames:
            _frame_dims(idx)
        payload = build_payload(
            mode=session.mode,
            classes=classes,
            data_path=session.data_path,
            frame_paths=frame_paths,
            frame_dims=_state.frame_dims,
            annotation_store=_state.annotation_store,
            reviewed=_state.reviewed_frames,
            image_ids=dict(_state.coco_image_ids),
            keypoint_specs=session.keypoint_specs,
        )
        coco_images = payload["images"]
        coco_annotations = payload["annotations"]
        categories = payload["categories"]
        if not coco_images:
            job.progress = 1.0
            job.status = "done"
            return

        # source_image_map: file_name (relativo) → imagem original, sem cópia intermediária
        by_name = {relative_name(p, session.data_path): p for p in frame_paths}
        source_image_map: dict[str, Path] = {img["file_name"]: by_name[img["file_name"]] for img in coco_images}
        frame_entries = [(None, by_name[img["file_name"]], img["file_name"], None) for img in coco_images]

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

            if session.mode == "keypoint":
                from app.annotation_keypoint.infrastructure.export.yolo_pose_exporter import (
                    export_yolo_pose_dataset,
                )

                export_yolo_pose_dataset(
                    payload,
                    output_dir=out,
                    source_images_dir=session.data_path,
                    split_ratios=job.split_ratios if job.use_split else None,
                    augmentation_preset=job.augmentation,
                    on_progress=_on_yolo_progress,
                )
            elif session.mode == "obb":
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
                    augmentation_preset=job.augmentation,
                )
            else:
                export_yolo_no_split(
                    payload,
                    source_images_dir=None,
                    dataset_root=out,
                    on_progress=_on_yolo_progress,
                    source_image_map=source_image_map,
                    augmentation_preset=job.augmentation,
                )

        if "coco" in job.formats:
            from app.annotation.infrastructure.export.coco_exporter import export_detection_coco_json
            from app.core.exporter import COCO_EXPORT_FILE_NAME

            coco_images_subdir = None if job.coco_layout == "roboflow" else "images"
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
                    split_out = out / split_name / COCO_EXPORT_FILE_NAME
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
                        images_subdir=coco_images_subdir,
                    )
                    running[0] += len(split_imgs)
            else:
                out_json = out / COCO_EXPORT_FILE_NAME
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
                    images_subdir=coco_images_subdir,
                )

        if job.zip_output:
            from app.core.export_package import verify_dataset_links, zip_dataset

            # Nada vai para o pacote sem as referências conferidas: imagem com o seu
            # label, file_name do COCO com a imagem ao lado.
            job.current_file = "Conferindo referências..."
            verify_dataset_links(out)

            def _on_zip_progress(done: int, zip_total: int, name: str) -> None:
                job.progress = done / max(zip_total, 1)
                job.current_file = f"Compactando: {name}"

            job.progress = 0.0
            job.zip_path = zip_dataset(out, on_progress=_on_zip_progress)

        job.progress = 1.0
        job.current_file = ""
        job.status = "done"

    except Exception as exc:
        job.status = "error"
        job.current_file = str(exc)


async def _run_export(export_id: str) -> None:
    """Delegate blocking file I/O to a worker thread so the event loop stays responsive."""
    await asyncio.to_thread(_run_export_blocking, export_id)


DEFAULT_AUGMENTATIONS = ("flip_h", "brightness", "contrast")


def _augmentation_preset(body):
    """Preset do catálogo existente; antes a opção era aceita e ignorada."""
    from app.annotation.core.augmentation.augmentation_types import (
        AUGMENTATION_CATALOG, AugEntry, AugmentationPreset,
    )

    if not body.augmentation:
        return None
    catalog = {item.key: item for item in AUGMENTATION_CATALOG}
    keys = body.augmentations or list(DEFAULT_AUGMENTATIONS)
    unknown = [k for k in keys if k not in catalog]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Augmentation desconhecida: {', '.join(unknown)}")
    entries = [
        AugEntry(key=k, enabled=True, params={p.key: p.default for p in catalog[k].params})
        for k in keys
    ]
    return AugmentationPreset(enabled=True, copies_per_image=body.augmentation_copies, entries=entries)


@router.get("/augmentations", response_model=list[AugmentationOption])
def list_augmentations() -> list:
    from app.annotation.core.augmentation.augmentation_types import AUGMENTATION_CATALOG

    return [AugmentationOption(key=i.key, label=i.label, description=i.description) for i in AUGMENTATION_CATALOG]


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
            zip_output=body.zip,
            augmentation=_augmentation_preset(body),
            coco_layout=body.coco_layout,
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
        output_path=str(job.output_path),
        zip_path=str(job.zip_path) if job.zip_path is not None else None,
    )
