"""Gravação de cada formato (YOLO do modo e COCO) a partir do payload do projeto."""

from __future__ import annotations

from typing import Callable

from app.annotation.core.export.split_service import assign_splits, normalize_split_ratios
from app.annotation.infrastructure.export import coco_exporter, yolo_exporter
from app.annotation_keypoint.infrastructure.export import yolo_pose_exporter
from app.annotation_obb.infrastructure.export import yolo_obb_exporter
from app.api.export.payload import ExportPayload
from app.core.exporter import COCO_EXPORT_FILE_NAME, ExportJob

ProgressFn = Callable[[int, int], None]
SPLITS = ("train", "val", "test")


def write_yolo(job: ExportJob, session, data: ExportPayload) -> None:
    """YOLO no formato do modo: pose (keypoint), OBB ou caixas (com ou sem split)."""
    payload, out = data.payload, job.output_path
    on_progress = _yolo_progress(job, data)
    split_ratios = job.split_ratios if job.use_split else None
    if session.mode == "keypoint":
        yolo_pose_exporter.export_yolo_pose_dataset(
            payload,
            output_dir=out,
            source_images_dir=session.data_path,
            split_ratios=split_ratios,
            augmentation_preset=job.augmentation,
            on_progress=on_progress,
        )
    elif session.mode == "obb":
        yolo_obb_exporter.export_yolo_obb_dataset(
            payload,
            output_dir=out,
            source_images_dir=None,
            split_ratios=split_ratios,
            source_image_map=data.source_image_map,
            on_progress=on_progress,
        )
    elif job.use_split:
        yolo_exporter.export_yolo_dataset(
            payload,
            source_images_dir=None,
            dataset_root=out,
            split_ratios=job.split_ratios,
            on_progress=on_progress,
            source_image_map=data.source_image_map,
            augmentation_preset=job.augmentation,
        )
    else:
        yolo_exporter.export_yolo_no_split(
            payload,
            source_images_dir=None,
            dataset_root=out,
            on_progress=on_progress,
            source_image_map=data.source_image_map,
            augmentation_preset=job.augmentation,
        )


def write_coco(job: ExportJob, data: ExportPayload) -> None:
    """_annotations.coco.json na raiz, ou um por pasta de split (train/val/test)."""
    images_subdir = None if job.coco_layout == "roboflow" else "images"
    total = len(data.images)
    if not job.use_split:
        coco_exporter.export_detection_coco_json(
            data.payload,
            output_path=job.output_path / COCO_EXPORT_FILE_NAME,
            source_images_dir=None,
            source_image_map=data.source_image_map,
            on_progress=_names_progress(job, [img["file_name"] for img in data.images], 0, total),
            images_subdir=images_subdir,
        )
        return

    assignments = assign_splits(data.images, normalize_split_ratios(job.split_ratios))
    by_split: dict[str, list[dict]] = {name: [] for name in SPLITS}
    for img in data.images:
        by_split[assignments.get(img["id"], "train")].append(img)

    done_before = 0
    for split_name in SPLITS:
        images = by_split[split_name]
        if not images:
            continue
        ids = {img["id"] for img in images}
        split_payload = {
            "images": images,
            "annotations": [ann for ann in data.payload["annotations"] if ann["image_id"] in ids],
            "categories": data.payload["categories"],
        }
        coco_exporter.export_detection_coco_json(
            split_payload,
            output_path=job.output_path / split_name / COCO_EXPORT_FILE_NAME,
            source_images_dir=None,
            source_image_map=data.source_image_map,
            on_progress=_names_progress(job, [img["file_name"] for img in images], done_before, total),
            images_subdir=images_subdir,
        )
        done_before += len(images)


def _yolo_progress(job: ExportJob, data: ExportPayload) -> ProgressFn:
    """Progresso do YOLO: os exportadores percorrem as imagens em ordem de file_name."""
    names = sorted(img["file_name"] for img in data.images)
    original = {name: path.name for name, path in data.source_image_map.items()}
    total = len(data.images)

    def on_progress(done: int, _total: int) -> None:
        job.progress = done / max(total, 1)
        if 0 < done <= len(names):
            job.current_file = original.get(names[done - 1], names[done - 1])

    return on_progress


def _names_progress(job: ExportJob, names: list[str], offset: int, total: int) -> ProgressFn:
    def on_progress(done: int, _total: int) -> None:
        job.progress = (offset + done) / max(total, 1)
        if 0 < done <= len(names):
            job.current_file = names[done - 1]

    return on_progress
