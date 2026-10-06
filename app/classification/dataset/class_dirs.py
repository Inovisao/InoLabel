"""Pastas de cada classe no dataset de saída (nome seguro, criar, remover)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Iterable

from app.core.session import normalize_class_names
from app.classification.dataset.files import unique_destination_path


def sanitize_class_dir_name(name: str) -> str:
    """Return a filesystem-safe directory name for a user-facing class."""

    cleaned = str(name).strip().lower()
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"[^a-z0-9._-]+", "_", cleaned)
    cleaned = cleaned.strip("._-")
    return cleaned or "classe"


def class_directories_for(classes: Iterable[str]) -> dict[str, str]:
    """Map class names to unique safe directory names."""

    directories: dict[str, str] = {}
    used: set[str] = set()
    for class_name in normalize_class_names(classes):
        base = sanitize_class_dir_name(class_name)
        candidate = base
        suffix = 1
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        directories[class_name] = candidate
        used.add(candidate)
    return directories


def prepare_dataset(output_dir: Path, classes: Iterable[str]) -> dict[str, str]:
    """Create one subdirectory per class and return class-to-folder mapping."""

    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    directories = class_directories_for(classes)
    for dirname in directories.values():
        (output_dir / dirname).mkdir(parents=True, exist_ok=True)
    return directories


def add_class_directory(output_dir: Path, class_name: str, class_directories: dict[str, str]) -> str:
    """Create a unique class subfolder and update ``class_directories``."""

    clean_name = str(class_name).strip()
    if not clean_name:
        raise ValueError("Nome de classe vazio.")
    if clean_name in class_directories:
        return class_directories[clean_name]

    used = set(class_directories.values())
    base = sanitize_class_dir_name(clean_name)
    candidate = base
    suffix = 1
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1

    (Path(output_dir).expanduser() / candidate).mkdir(parents=True, exist_ok=True)
    class_directories[clean_name] = candidate
    return candidate


def class_directory_path(output_dir: Path, class_name: str, class_directories: dict[str, str]) -> Path | None:
    """Return the filesystem path for a class directory."""

    dirname = class_directories.get(class_name)
    if not dirname:
        return None
    return Path(output_dir).expanduser() / dirname


def class_directory_has_files(output_dir: Path, class_name: str, class_directories: dict[str, str]) -> bool:
    """Return True when the class folder contains any file."""

    path = class_directory_path(output_dir, class_name, class_directories)
    if path is None or not path.exists():
        return False
    return any(candidate.is_file() for candidate in path.rglob("*"))


def remove_class_directory(
    output_dir: Path,
    class_name: str,
    class_directories: dict[str, str],
    *,
    delete_files: bool = False,
    archive_files: bool = False,
) -> Path | None:
    """Remove class mapping and optionally delete its folder from disk."""

    path = class_directory_path(output_dir, class_name, class_directories)
    class_directories.pop(class_name, None)
    if delete_files and path is not None and path.exists():
        shutil.rmtree(path)
    elif archive_files and path is not None and path.exists():
        archive_root = unique_destination_path(Path(output_dir).expanduser() / "_removed" / path.name)
        archive_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(archive_root))
    elif path is not None and path.exists():
        try:
            path.rmdir()
        except OSError:
            pass
    return path
