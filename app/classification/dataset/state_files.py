"""Arquivo classification_state.json: localizar, ler, gravar e listar saídas anteriores."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from app.config import OUTPUT_DATASET_PREFIX
from app.core.session import normalize_class_names
from app.classification.dataset.models import STATE_FILE_NAME, ClassificationOutputState, ClassificationRecord, ClassificationState


STATE_PATTERN = re.compile(rf"^{re.escape(OUTPUT_DATASET_PREFIX)}(?P<index>\d+)_(?P<stamp>\d{{8}}_\d{{6}})")


NEW_STATE_PATTERN = re.compile(r"^.+_(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<hour>\d{2}):(?P<minute>\d{2})(?:_\d{3})?$")


def find_state_path(path: Path) -> Path | None:
    """Return a classification state path from a file or output directory."""

    path = Path(path).expanduser()
    if path.is_file() and path.name == STATE_FILE_NAME:
        return path
    if path.is_dir():
        candidate = path / STATE_FILE_NAME
        if candidate.exists():
            return candidate
    return None


def load_state(state_path: Path) -> ClassificationState | None:
    """Load a classification state file if it exists."""

    state_path = Path(state_path).expanduser()
    if not state_path.exists():
        return None
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    task_mode = str(payload.get("task_mode", "")).strip()
    if task_mode and task_mode != "classification":
        raise ValueError(f"Estado nao e de classificacao: {task_mode}")
    if "categories" in payload or "annotations" in payload:
        raise ValueError("Estado COCO nao pode ser usado como estado de classificacao.")
    records = tuple(
        ClassificationRecord(
            source_path=Path(item["source_path"]).expanduser(),
            destination_path=Path(item["destination_path"]).expanduser(),
            class_name=str(item["class_name"]),
            classified_at=str(item.get("classified_at", "")),
            operation=str(item.get("operation", "copy")),
        )
        for item in payload.get("records", [])
        if item.get("source_path") and item.get("destination_path") and item.get("class_name")
    )
    return ClassificationState(
        classes=normalize_class_names(payload.get("classes", [])),
        class_directories=dict(payload.get("class_directories", {})),
        source_root=Path(payload.get("source_root", "")).expanduser(),
        records=records,
    )


def load_required_state(path: Path) -> ClassificationState:
    """Load a classification state from a file or output directory."""

    state_path = find_state_path(path)
    if state_path is None:
        raise FileNotFoundError(f"Arquivo {STATE_FILE_NAME} nao encontrado em: {path}")
    state = load_state(state_path)
    if state is None:
        raise FileNotFoundError(f"Arquivo {STATE_FILE_NAME} nao encontrado em: {path}")
    return state


def write_state(
    state_path: Path,
    *,
    classes: Iterable[str],
    class_directories: dict[str, str],
    source_root: Path,
    records: Iterable[ClassificationRecord],
):
    """Persist classification progress."""

    payload = {
        "task_mode": "classification",
        "source_root": str(Path(source_root).expanduser()),
        "classes": list(normalize_class_names(classes)),
        "class_directories": dict(class_directories),
        "records": [
            {
                "source_path": str(record.source_path),
                "destination_path": str(record.destination_path),
                "class_name": record.class_name,
                "classified_at": record.classified_at,
                "operation": record.operation,
            }
            for record in records
        ],
    }
    # Written on every classified image; compact output keeps the cost flat as the
    # record list grows. Read back via load_state, never by hand.
    state_path = Path(state_path)
    tmp_path = state_path.with_name(f"{state_path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp_path, state_path)


def list_output_states(outputs_dir: Path) -> list[ClassificationOutputState]:
    """List classification output states ordered from oldest to newest."""

    outputs_dir = Path(outputs_dir).expanduser()
    if not outputs_dir.exists():
        return []
    states = []
    for child in outputs_dir.iterdir():
        if not child.is_dir():
            continue
        state_path = find_state_path(child)
        if state_path is None:
            continue
        try:
            state = load_state(state_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if state is None:
            continue
        index, created_at = _parse_state_name(child.name)
        states.append(
            ClassificationOutputState(
                path=child,
                state_path=state_path,
                index=index,
                created_at=created_at,
                modified_at=_modified_at(state_path),
                class_names=state.classes,
                image_count=len(state.records),
                source_root=state.source_root,
            )
        )
    return sorted(states, key=lambda item: (item.modified_at or item.created_at or datetime.min, item.path.name))


def list_output_states_for_sources(
    sources: Iterable[Path],
    outputs_dir: Path,
) -> list[ClassificationOutputState]:
    """List classification states associated with selected source paths."""

    project_sources = _normalize_paths(sources)
    if not project_sources:
        return []
    # Caminho identico, nao "um dentro do outro": senao uma pasta nova dentro de um
    # dataset antigo retoma o estado antigo (ver app/core/output_state.py).
    return [
        state for state in list_output_states(outputs_dir)
        if any(_same_path(source, state.source_root) for source in project_sources)
    ]


def latest_output_state_for_sources(
    sources: Iterable[Path],
    outputs_dir: Path,
) -> ClassificationOutputState | None:
    states = list_output_states_for_sources(sources, outputs_dir)
    if not states:
        return None
    return states[-1]


def _parse_state_name(name: str) -> tuple[int, Optional[datetime]]:
    match = STATE_PATTERN.match(name)
    if match:
        try:
            created_at = datetime.strptime(match.group("stamp"), "%Y%m%d_%H%M%S")
        except ValueError:
            created_at = None
        return int(match.group("index")), created_at
    match = NEW_STATE_PATTERN.match(name)
    if match:
        try:
            created_at = datetime(
                datetime.now().year,
                int(match.group("month")),
                int(match.group("day")),
                int(match.group("hour")),
                int(match.group("minute")),
            )
        except ValueError:
            created_at = None
        return 0, created_at
    return 0, None


def _modified_at(path: Path) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime)
    except OSError:
        return None


def _normalize_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    normalized = []
    seen = set()
    for raw_path in paths:
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        try:
            path = path.resolve()
        except OSError:
            path = path.absolute()
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(path)
    return tuple(normalized)


def _same_path(left: Path, right: Path) -> bool:
    # Path("") vira "." (pasta atual): estado sem source_root nao pertence a dataset nenhum.
    if str(left) in ("", ".") or str(right) in ("", "."):
        return False
    normalized = _normalize_paths((left, right))
    return len(normalized) == 1  # os dois viraram o mesmo caminho resolvido
