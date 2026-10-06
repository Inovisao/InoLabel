"""Exportação YOLO de caixas: com split train/val/test ou tudo em ``all/``."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.annotation.core.augmentation.augmentation_types import AugmentationPreset
from app.annotation.core.export.split_service import assign_splits, normalize_split_ratios
from app.annotation.core.export.yolo_label_service import (
    build_zero_based_category_mapping,
    format_yaml,
    format_yaml_no_split,
)
from app.annotation.infrastructure.export.export_dir import reset_export_dir
from app.annotation.infrastructure.export.yolo_jobs import ImageResult, plan_jobs, run_jobs, write_text_atomic

SPLITS = ("train", "val", "test")


def _normalized_split_ratios(split_ratios: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return normalize_split_ratios(split_ratios)


def export_yolo_dataset(
    payload: Dict[str, Any],
    source_images_dir: Optional[Path],
    dataset_root: Path,
    split_ratios: Tuple[float, float, float] = (0.8, 0.1, 0.1),
    augmentation_preset: Optional[AugmentationPreset] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    source_image_map: Optional[Dict[str, Path]] = None,
) -> Dict[str, Any]:
    """Dataset com images/{train,val,test} e labels/; augmentation só no treino."""
    normalized_ratios = _normalized_split_ratios(split_ratios)
    names, class_mapping = _start(payload, dataset_root, SPLITS)
    assignments = assign_splits(payload.get("images", []), normalized_ratios)

    malformed: List[str] = []
    jobs = plan_jobs(
        payload, dataset_root, lambda image_id: assignments.get(image_id, "train"),
        source_images_dir, source_image_map, malformed,
    )
    results = run_jobs(
        jobs, class_mapping, augmentation_preset, lambda split: split == "train",
        on_progress, total=len(payload.get("images", [])),
    )

    images_per_split = {split: 0 for split in SPLITS}
    labels_per_split = {split: 0 for split in SPLITS}
    empty_images_per_split = {split: 0 for split in SPLITS}
    for result in results:
        images_per_split[result.split] += result.images_written
        labels_per_split[result.split] += result.labels_written
        if result.is_empty:
            empty_images_per_split[result.split] += 1

    data_yaml = _write_data_yaml(dataset_root, format_yaml(dataset_root, names))
    return {
        "dataset_root": dataset_root.resolve(),
        "data_yaml": data_yaml.resolve(),
        "images_per_split": images_per_split,
        "labels_per_split": labels_per_split,
        "empty_images_per_split": empty_images_per_split,
        **_summary(results, malformed, names),
    }


def export_yolo_no_split(
    payload: Dict[str, Any],
    source_images_dir: Optional[Path],
    dataset_root: Path,
    augmentation_preset: Optional[AugmentationPreset] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    source_image_map: Optional[Dict[str, Path]] = None,
) -> Dict[str, Any]:
    """Dataset com tudo em images/all e labels/all."""
    names, class_mapping = _start(payload, dataset_root, ("all",))
    malformed: List[str] = []
    jobs = plan_jobs(payload, dataset_root, lambda _id: "all", source_images_dir, source_image_map, malformed)
    results = run_jobs(
        jobs, class_mapping, augmentation_preset, lambda _split: True,
        on_progress, total=len(payload.get("images", [])),
    )
    data_yaml = _write_data_yaml(dataset_root, format_yaml_no_split(dataset_root, names))
    return {
        "dataset_root": dataset_root.resolve(),
        "data_yaml": data_yaml.resolve(),
        "total_images": sum(r.images_written for r in results),
        "total_labels": sum(r.labels_written for r in results),
        **_summary(results, malformed, names),
    }


def _start(payload: Dict[str, Any], dataset_root: Path, splits) -> Tuple[Dict[int, str], Dict[int, int]]:
    # Só recria pastas vazias ou criadas pelo InoLabel (marcador .inolabel_export);
    # qualquer outra pasta existente é recusada sem apagar nada.
    reset_export_dir(dataset_root)
    class_mapping, names = build_zero_based_category_mapping(payload.get("categories", []))
    if not names:
        raise ValueError("No valid categories found for YOLO export.")
    for split in splits:
        (dataset_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_root / "labels" / split).mkdir(parents=True, exist_ok=True)
    return names, class_mapping


def _summary(results: List[ImageResult], malformed: List[str], names: Dict[int, str]) -> Dict[str, Any]:
    present: Set[int] = set()
    for result in results:
        malformed.extend(result.malformed)
        present.update(result.present_classes)
    return {
        "images_without_annotation": [r.file_name for r in results if r.is_empty],
        "malformed_labels": malformed,
        "classes_present": {class_id: names[class_id] for class_id in sorted(present)},
        "names": names,
    }


def _write_data_yaml(dataset_root: Path, text: str) -> Path:
    path = dataset_root / "data.yaml"
    write_text_atomic(path, text)
    return path
