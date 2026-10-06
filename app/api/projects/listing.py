"""Listagem de projetos e de saídas antigas numa pasta (sem recursão além de 1 nível)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import OUTPUT_BASE


def list_outputs(output_path: str):
    root = Path(output_path).expanduser()
    if not root.exists():
        return []
    sessions = []
    for child in sorted((item for item in root.iterdir() if item.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True):
        sessions.append(
            {
                "name": child.name,
                "mode": "unknown",
                "frame_count": 0,
                "created_at": datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
        )
    return sessions


def list_projects(path: str = "") -> list:
    """List InoLabel annotation projects under *path* (defaults to OUTPUT_BASE).

    A directory is considered a project when it contains a ``.inolabel.json``
    metadata file written by ``POST /session/start``.  Falls back to scanning
    any directory that has a ``labels/`` subdirectory (legacy projects that
    pre-date the metadata file).
    """
    root = Path(path).expanduser().resolve() if path else OUTPUT_BASE
    if not root.exists():
        return []

    projects = []
    try:
        candidates = sorted(
            (item for item in root.iterdir() if item.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return []

    for child in candidates:
        # -- Read .inolabel.json metadata if present --
        meta: dict = {}
        meta_file = child / ".inolabel.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        labels_dir = child / "labels"
        has_labels = labels_dir.is_dir()
        if not meta and not has_labels:
            continue  # not a project directory

        # -- Count annotated frames (non-empty .txt files in labels/) --
        annotated = 0
        if has_labels:
            try:
                annotated = sum(
                    1 for f in labels_dir.rglob("*.txt") if f.stat().st_size > 0
                )
            except OSError:
                pass
        # Classificação não gera labels/: conta os registros do estado (um por imagem).
        classification_state = child / "classification_state.json"
        if classification_state.is_file():
            try:
                records = json.loads(classification_state.read_text(encoding="utf-8")).get("records", [])
                annotated = max(annotated, len(records))
            except (OSError, ValueError, AttributeError):
                pass

        # -- Class names: prefer metadata, fall back to classes.txt --
        classes: list[str] = meta.get("classes") or []
        if not classes:
            classes_txt = child / "classes.txt"
            if classes_txt.exists():
                try:
                    classes = [
                        ln.strip()
                        for ln in classes_txt.read_text(encoding="utf-8").splitlines()
                        if ln.strip()
                    ]
                except OSError:
                    pass

        try:
            stat = child.stat()
            created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
            last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            continue

        projects.append(
            {
                "name": child.name,
                "path": str(child),
                "data_path": meta.get("data_path", ""),
                "mode": meta.get("mode", "unknown"),
                "annotated_frames": annotated,
                "classes": classes,
                "created_at": created_at,
                "last_modified": last_modified,
            }
        )

    return projects
