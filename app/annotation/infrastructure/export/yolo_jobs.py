"""Etapas comuns da exportação YOLO de caixas: planejar os arquivos e gravá-los em paralelo.

1. ``plan_jobs`` (sequencial): resolve origem e destino de cada imagem, recusa nomes
   repetidos e caminhos que saiam da pasta.
2. ``run_jobs`` (paralelo): copia a imagem, grava o label de forma atômica e, quando
   pedido, as cópias aumentadas.
"""

from __future__ import annotations

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import cv2

from app.annotation.core.augmentation.augmentation_service import apply_preset
from app.annotation.core.augmentation.augmentation_types import AugmentationPreset
from app.annotation.core.export.yolo_label_service import annotations_to_yolo_bboxes, format_yolo_boxes

ProgressFn = Callable[[int, int], None]


@dataclass
class ImageJob:
    file_name: str
    split: str
    source: Path
    target_image: Path
    target_label: Path
    annotations: List[Dict[str, Any]]
    width: int
    height: int

    @property
    def is_empty(self) -> bool:
        return not self.annotations


@dataclass
class ImageResult:
    file_name: str
    split: str
    is_empty: bool
    images_written: int
    labels_written: int
    malformed: List[str] = field(default_factory=list)
    present_classes: Set[int] = field(default_factory=set)


def safe_resolve_within(root: Path, *parts: str) -> Path:
    """Junta ``parts`` a ``root`` e garante que o resultado continua dentro de ``root``.

    ValueError se o caminho escapar (impede path traversal pelo file_name).
    """
    root_resolved = root.resolve()
    dest = root_resolved.joinpath(*parts).resolve()
    if dest != root_resolved and root_resolved not in dest.parents:
        raise ValueError(f"Resolved path escapes allowed root: {dest}")
    return dest


def annotations_by_image(payload: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for ann in payload.get("annotations", []):
        grouped.setdefault(int(ann.get("image_id")), []).append(ann)
    return grouped


def resolve_source(
    file_name: str,
    source_images_dir: Optional[Path],
    source_image_map: Optional[Dict[str, Path]],
) -> Path:
    """Imagem original do file_name: pelo mapa, quando há, senão pela pasta de origem."""
    if source_image_map is not None:
        src = source_image_map.get(file_name)
        if src is None or not src.exists():
            raise FileNotFoundError(f"Image not found for export: {file_name}")
        return src
    if source_images_dir is None:
        raise ValueError("Either source_images_dir or source_image_map must be provided.")
    src = safe_resolve_within(source_images_dir, file_name)
    if not src.exists():
        raise FileNotFoundError(f"Image not found for export: {src}")
    return src


def plan_jobs(
    payload: Dict[str, Any],
    dataset_root: Path,
    split_of: Callable[[int], str],
    source_images_dir: Optional[Path],
    source_image_map: Optional[Dict[str, Path]],
    malformed: List[str],
) -> List[ImageJob]:
    """Um job por imagem, em ordem de file_name. file_name vazio vai para ``malformed``."""
    grouped = annotations_by_image(payload)
    seen: Set[str] = set()
    jobs: List[ImageJob] = []
    for image in sorted(payload.get("images", []), key=lambda item: str(item.get("file_name", ""))):
        image_id = int(image.get("id"))
        file_name = str(image.get("file_name", "")).strip()
        if not file_name:
            malformed.append(f"image_id {image_id}: file_name is empty")
            continue
        if file_name in seen:
            raise ValueError(f"Duplicate image name found: {file_name}")
        seen.add(file_name)
        split = split_of(image_id)
        jobs.append(ImageJob(
            file_name=file_name,
            split=split,
            source=resolve_source(file_name, source_images_dir, source_image_map),
            target_image=safe_resolve_within(dataset_root / "images" / split, file_name),
            target_label=safe_resolve_within(
                dataset_root / "labels" / split, Path(file_name).with_suffix(".txt").as_posix()
            ),
            annotations=grouped.get(image_id, []),
            width=int(image.get("width", 0)),
            height=int(image.get("height", 0)),
        ))
    return jobs


def run_jobs(
    jobs: List[ImageJob],
    class_mapping: Dict[int, int],
    augmentation_preset: Optional[AugmentationPreset],
    augment: Callable[[str], bool],
    on_progress: Optional[ProgressFn],
    total: int,
) -> List[ImageResult]:
    """Executa os jobs em paralelo; ``augment(split)`` diz se o split recebe cópias aumentadas."""
    lock = threading.Lock()
    done = [0]
    results: List[ImageResult] = []

    def process(job: ImageJob) -> ImageResult:
        result = ImageResult(job.file_name, job.split, job.is_empty, 0, 0)
        job.target_image.parent.mkdir(parents=True, exist_ok=True)
        job.target_label.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(job.source, job.target_image)
        boxes = annotations_to_yolo_bboxes(
            job.annotations, class_mapping, job.width, job.height,
            result.malformed, result.present_classes, job.target_label.name,
        )
        write_text_atomic(job.target_label, format_yolo_boxes(boxes))
        aug_images = aug_labels = 0
        if augment(job.split):
            aug_images, aug_labels = write_augmented_copies(
                job.source, job.target_image, job.target_label, boxes,
                augmentation_preset, result.malformed, result.present_classes,
            )
        result.images_written = 1 + aug_images
        result.labels_written = len(boxes) + aug_labels
        return result

    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 4)) as executor:
        for future in as_completed([executor.submit(process, job) for job in jobs]):
            results.append(future.result())
            with lock:
                done[0] += 1
                if on_progress:
                    on_progress(done[0], total)
    return results


def write_augmented_copies(
    source_image_path: Path,
    target_image_path: Path,
    target_label_path: Path,
    yolo_boxes: List[List[Any]],
    augmentation_preset: Optional[AugmentationPreset],
    malformed_labels: List[str],
    present_classes: Set[int],
) -> Tuple[int, int]:
    """Grava as cópias aumentadas (<nome>_augN) ao lado da imagem; devolve (imagens, caixas)."""
    if augmentation_preset is None or not augmentation_preset.enabled:
        return 0, 0
    image = cv2.imread(str(source_image_path))
    if image is None:
        malformed_labels.append(f"{target_image_path.name}: failed to read image for augmentation")
        return 0, 0

    written_images = written_labels = 0
    for idx, (aug_image, aug_boxes) in enumerate(apply_preset(image, yolo_boxes, augmentation_preset)):
        aug_image_path = target_image_path.with_name(
            f"{target_image_path.stem}_aug{idx + 1}{target_image_path.suffix}"
        )
        aug_label_path = target_label_path.with_name(f"{target_label_path.stem}_aug{idx + 1}.txt")
        if not cv2.imwrite(str(aug_image_path), aug_image):
            malformed_labels.append(f"{aug_image_path.name}: failed to save augmented image")
            continue
        aug_label_path.write_text(format_yolo_boxes(aug_boxes), encoding="utf-8")
        for box in aug_boxes:
            if len(box) == 5:
                present_classes.add(int(box[0]))
        written_images += 1
        written_labels += len(aug_boxes)
    return written_images, written_labels


def write_text_atomic(path: Path, text: str) -> None:
    """Grava via .tmp + replace: um erro no meio não deixa arquivo truncado."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
