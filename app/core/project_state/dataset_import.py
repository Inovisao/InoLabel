"""Discover and combine COCO annotations stored alongside a dataset."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Optional

from app.annotation.infrastructure.persistence.state_file import AnnotationStateUnreadableError


def import_dataset_coco(data_path: Path, output_path: Path) -> Optional[dict]:
    """Return a normalized COCO payload from dataset annotation files, if present.

    Source files are only read. Image names are normalized against the selected
    dataset root so split layouts such as ``train/_annotations.coco.json`` work.
    """
    root = Path(data_path)
    if not root.is_dir():
        return None
    output = Path(output_path).resolve()
    files = [path for path in root.rglob("*") if path.is_file() and _is_coco_candidate(path)]
    state_dir = output / "saved_data_states"
    files = [path for path in files if not _is_inside(path.resolve(), state_dir)]
    if not files:
        return None

    categories_by_name: dict[str, dict] = {}
    images_by_name: dict[str, dict] = {}
    annotations: list[dict] = []
    next_annotation_id = 1

    for source in sorted(files):
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise AnnotationStateUnreadableError(source, exc) from exc
        if not isinstance(payload, dict) or not all(
            isinstance(payload.get(key), list) for key in ("images", "annotations", "categories")
        ):
            raise AnnotationStateUnreadableError(source, ValueError("o JSON não contém as listas COCO esperadas"))

        local_categories = {}
        for category in payload["categories"]:
            if not isinstance(category, dict) or "id" not in category or not str(category.get("name", "")).strip():
                continue
            name = str(category["name"]).strip()
            if name not in categories_by_name:
                normalized = dict(category)
                normalized["id"] = len(categories_by_name) + 1
                categories_by_name[name] = normalized
            local_categories[category["id"]] = categories_by_name[name]["id"]

        local_images = {}
        for image in payload["images"]:
            if not isinstance(image, dict) or "id" not in image:
                continue
            name = _dataset_relative_name(root, source.parent, image.get("file_name", ""))
            if not name:
                continue
            if name not in images_by_name:
                normalized = dict(image)
                normalized["id"] = len(images_by_name) + 1
                normalized["file_name"] = name
                images_by_name[name] = normalized
            local_images[image["id"]] = images_by_name[name]["id"]

        for annotation in payload["annotations"]:
            if not isinstance(annotation, dict):
                continue
            image_id = local_images.get(annotation.get("image_id"))
            category_id = local_categories.get(annotation.get("category_id"))
            if image_id is None or category_id is None:
                continue
            normalized = dict(annotation)
            normalized.update(id=next_annotation_id, image_id=image_id, category_id=category_id)
            annotations.append(normalized)
            next_annotation_id += 1

    return {
        "info": {"description": "Imported dataset COCO annotations"},
        "licenses": [],
        "categories": list(categories_by_name.values()),
        "images": list(images_by_name.values()),
        "annotations": annotations,
    }


def write_import_if_missing(path: Path, payload: dict) -> bool:
    """Atomically create a project copy without replacing a file created meanwhile."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temp_path = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp_path, path)
            return True
        except FileExistsError:
            return False
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _is_coco_candidate(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.endswith(".coco.json")
        or name.startswith("annotations") and name.endswith(".json")
        or name.startswith("instances") and name.endswith(".json")
    )


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _dataset_relative_name(root: Path, annotation_dir: Path, file_name) -> str:
    name = str(file_name or "").strip()
    if not name:
        return ""
    image_path = Path(name)
    candidates = [image_path] if image_path.is_absolute() else [annotation_dir / image_path, root / image_path]
    for candidate in candidates:
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            continue
    return image_path.name
