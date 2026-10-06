"""Imagens de origem: descoberta (pasta ou lista .txt) e se já foram usadas."""

from __future__ import annotations

import re
from pathlib import Path

from app.config import IMAGE_EXTENSIONS


def discover_images(data_root: Path) -> list[Path]:
    """Discover images from a folder, single image, or text list."""

    data_root = Path(data_root).expanduser()
    if data_root.is_file() and data_root.suffix.lower() in IMAGE_EXTENSIONS:
        return [data_root]
    if data_root.is_file() and data_root.suffix.lower() in {".txt", ".lst"}:
        return _read_image_list(data_root)
    if data_root.is_dir():
        return sorted(path for path in data_root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
    return []


def _read_image_list(list_path: Path) -> list[Path]:
    base_dir = list_path.parent
    images = []
    for raw_line in list_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        path = Path(line).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(path)
    return images


def source_looks_used(image_path: Path, output_dir: Path, class_directories: dict[str, str]) -> bool:
    """Return True when an image name already exists in any class subfolder.

    This is a legacy fallback only. The primary filter uses exact source paths
    persisted in ``classification_state.json``.
    """

    image_path = Path(image_path)
    output_dir = Path(output_dir).expanduser()
    for dirname in class_directories.values():
        class_dir = output_dir / dirname
        if not class_dir.is_dir():
            continue
        if any(candidate.is_file() and _same_original_name(candidate.name, image_path.name) for candidate in class_dir.iterdir()):
            return True
    return False


def _same_original_name(candidate_name: str, source_name: str) -> bool:
    source = Path(source_name)
    candidate = Path(candidate_name)
    if candidate_name == source_name:
        return True
    pattern = re.compile(rf"^{re.escape(source.stem)}__\d{{3}}{re.escape(source.suffix)}$")
    return bool(pattern.match(candidate.name))
