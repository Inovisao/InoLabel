"""Classificar uma imagem (copiar/mover/registrar), reclassificar, desfazer e exportar o dataset."""

from __future__ import annotations

import shutil
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.core.session import normalize_class_names
from app.classification.dataset.class_dirs import class_directories_for
from app.classification.dataset.files import unique_destination_path
from app.classification.dataset.models import ClassificationRecord


def classify_image_source(
    image_path: Path,
    *,
    class_name: str,
    output_dir: Path,
    class_directories: dict[str, str],
) -> ClassificationRecord:
    """Record the selected class for an image without touching image files."""

    image_path = Path(image_path).expanduser()
    class_dir = class_directories[class_name]
    destination_path = Path(output_dir).expanduser() / class_dir / image_path.name
    return ClassificationRecord(
        source_path=image_path,
        destination_path=destination_path,
        class_name=class_name,
        classified_at=datetime.now().isoformat(timespec="seconds"),
        operation="state",
    )


def transfer_image_to_class(
    image_path: Path,
    *,
    class_name: str,
    output_dir: Path,
    class_directories: dict[str, str],
    move: bool = False,
) -> ClassificationRecord:
    """Copy or move an image into the selected class directory."""

    image_path = Path(image_path).expanduser()
    class_dir = class_directories[class_name]
    destination_dir = Path(output_dir).expanduser() / class_dir
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = unique_destination_path(destination_dir / image_path.name)
    if move:
        shutil.move(str(image_path), str(destination_path))
    else:
        shutil.copy2(image_path, destination_path)
    return ClassificationRecord(
        source_path=image_path,
        destination_path=destination_path,
        class_name=class_name,
        classified_at=datetime.now().isoformat(timespec="seconds"),
        operation="move" if move else "copy",
    )


def copy_image_to_class(
    image_path: Path,
    *,
    class_name: str,
    output_dir: Path,
    class_directories: dict[str, str],
) -> ClassificationRecord:
    """Copy an image into the selected class directory."""

    return transfer_image_to_class(
        image_path,
        class_name=class_name,
        output_dir=output_dir,
        class_directories=class_directories,
        move=False,
    )


def reclassify_record(
    record: ClassificationRecord,
    *,
    class_name: str,
    output_dir: Path,
    class_directories: dict[str, str],
) -> ClassificationRecord:
    """Move a imagem já classificada para a pasta da nova classe, sem duplicar.

    Antes, reclassificar copiava de novo: a mesma imagem ficava nas duas pastas e
    com dois registros, ou seja, em duas classes ao mesmo tempo.
    """
    if record.class_name == class_name:
        return record
    destination_dir = Path(output_dir).expanduser() / class_directories[class_name]
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = unique_destination_path(destination_dir / record.destination_path.name)
    if record.destination_path.exists():
        shutil.move(str(record.destination_path), str(destination_path))
    elif record.operation == "copy" and record.source_path.exists():
        shutil.copy2(record.source_path, destination_path)
    return replace(
        record,
        destination_path=destination_path,
        class_name=class_name,
        classified_at=datetime.now().isoformat(timespec="seconds"),
    )


def undo_record(record: ClassificationRecord) -> None:
    """Desfaz a classificação: apaga a cópia, ou devolve a imagem movida ao lugar original."""
    destination = record.destination_path
    if not destination.exists():
        return
    if record.operation == "move":
        if not record.source_path.exists():
            record.source_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(record.source_path))
        return
    destination.unlink()


def export_classification_dataset(
    *,
    records: Iterable[ClassificationRecord],
    classes: Iterable[str],
    class_directories: dict[str, str],
    dataset_root: Path,
) -> dict[str, object]:
    """Export classified images into class subfolders from the JSON state."""

    dataset_root = Path(dataset_root).expanduser()
    directories = dict(class_directories)
    for class_name, dirname in class_directories_for(classes).items():
        directories.setdefault(class_name, dirname)
    for dirname in directories.values():
        (dataset_root / dirname).mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped: list[str] = []
    exported_by_class = {class_name: 0 for class_name in normalize_class_names(classes)}
    for record in _latest_records_by_source(records):
        if record.class_name not in directories:
            skipped.append(str(record.source_path))
            continue
        source_path = _existing_record_image_path(record)
        if source_path is None:
            skipped.append(str(record.source_path))
            continue

        destination_dir = dataset_root / directories[record.class_name]
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_path = unique_destination_path(destination_dir / Path(record.source_path).name)
        shutil.copy2(source_path, destination_path)
        copied += 1
        exported_by_class[record.class_name] = exported_by_class.get(record.class_name, 0) + 1

    return {
        "dataset_root": dataset_root,
        "copied": copied,
        "skipped": skipped,
        "by_class": exported_by_class,
    }


def _existing_record_image_path(record: ClassificationRecord) -> Path | None:
    source_path = Path(record.source_path).expanduser()
    if source_path.exists():
        return source_path
    destination_path = Path(record.destination_path).expanduser()
    if destination_path.exists():
        return destination_path
    return None


def _latest_records_by_source(records: Iterable[ClassificationRecord]) -> tuple[ClassificationRecord, ...]:
    latest: dict[Path, ClassificationRecord] = {}
    order: list[Path] = []
    for record in records:
        source_path = Path(record.source_path).expanduser()
        if source_path not in latest:
            order.append(source_path)
        latest[source_path] = record
    return tuple(latest[source_path] for source_path in order)
