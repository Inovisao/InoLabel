"""Output dataset state management.

Each annotation run writes to an isolated directory under ``outputs/``. Existing
states can be resumed or used as a template for classes/configuration.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from app.config import OUTPUT_DATASET_PREFIX, OUTPUTS_DIR
from app.core.session import AnnotationTaskMode, normalize_class_names

ANNOTATION_FILE_NAMES = ("annotations.coco.json", "__annotations.coco.json")
STATE_PATTERN = re.compile(rf"^{re.escape(OUTPUT_DATASET_PREFIX)}(?P<index>\d+)_(?P<stamp>\d{{8}}_\d{{6}})$")


@dataclass(frozen=True)
class OutputState:
    """Summary of a persisted annotation state."""

    path: Path
    annotations_path: Path
    index: int
    created_at: Optional[datetime]
    task_mode: Optional[AnnotationTaskMode]
    class_names: tuple[str, ...]
    image_count: int
    annotation_count: int

    @property
    def label(self) -> str:
        mode = self.task_mode.label if self.task_mode is not None else "modo desconhecido"
        stamp = self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else self.path.name
        return (
            f"{self.path.name} | {stamp} | {mode} | "
            f"{len(self.class_names)} classes | {self.image_count} imagens | {self.annotation_count} anotacoes"
        )


@dataclass(frozen=True)
class LoadedAnnotationState:
    """Data read from a COCO annotations file."""

    annotations_path: Path
    output_dir: Path
    task_mode: Optional[AnnotationTaskMode]
    class_names: tuple[str, ...]
    categories: tuple[dict, ...]
    image_count: int
    annotation_count: int


def annotations_path_for(output_dir: Path) -> Path:
    """Canonical annotations path for new output states."""

    return Path(output_dir) / ANNOTATION_FILE_NAMES[0]


def find_annotations_path(path: Path) -> Optional[Path]:
    """Return a supported annotations file from a file or output directory."""

    path = Path(path).expanduser()
    if path.is_file() and path.name in ANNOTATION_FILE_NAMES:
        return path
    if path.is_dir():
        for name in ANNOTATION_FILE_NAMES:
            candidate = path / name
            if candidate.exists():
                return candidate
    return None


def list_output_states(outputs_dir: Path = OUTPUTS_DIR) -> list[OutputState]:
    """List valid output states ordered from oldest to newest."""

    outputs_dir = Path(outputs_dir).expanduser()
    if not outputs_dir.exists():
        return []
    states = []
    for child in outputs_dir.iterdir():
        if not child.is_dir():
            continue
        annotations_path = find_annotations_path(child)
        if annotations_path is None:
            continue
        state = _build_state(child, annotations_path)
        if state is not None:
            states.append(state)
    return sorted(states, key=lambda state: (state.index, state.created_at or datetime.min, state.path.name))


def latest_output_state(outputs_dir: Path = OUTPUTS_DIR) -> Optional[OutputState]:
    """Return the newest available output state."""

    states = list_output_states(outputs_dir)
    if not states:
        return None
    return states[-1]


def create_new_output_dir(
    outputs_dir: Path = OUTPUTS_DIR,
    *,
    now: Optional[datetime] = None,
    prefix: str = OUTPUT_DATASET_PREFIX,
) -> Path:
    """Create a unique output state directory using index and timestamp."""

    outputs_dir = Path(outputs_dir).expanduser()
    outputs_dir.mkdir(parents=True, exist_ok=True)
    index = _next_index(outputs_dir, prefix=prefix)
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    candidate = outputs_dir / f"{prefix}{index}_{stamp}"
    suffix = 1
    while candidate.exists():
        candidate = outputs_dir / f"{prefix}{index}_{stamp}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    (candidate / "images").mkdir(parents=True, exist_ok=True)
    return candidate


def load_annotation_state(path: Path) -> LoadedAnnotationState:
    """Load categories/configuration from a supported annotations file or state directory."""

    annotations_path = find_annotations_path(path)
    if annotations_path is None:
        raise FileNotFoundError(f"Arquivo de anotacoes nao encontrado em: {path}")
    try:
        payload = json.loads(annotations_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pylint: disable=broad-except
        raise ValueError(f"Nao foi possivel ler {annotations_path}: {exc}") from exc

    categories = tuple(dict(cat) for cat in payload.get("categories", []) if str(cat.get("name", "")).strip())
    class_names = normalize_class_names(str(cat.get("name", "")) for cat in categories)
    info = payload.get("info", {}) if isinstance(payload.get("info"), dict) else {}
    mode = _parse_mode(info.get("task_mode"))
    return LoadedAnnotationState(
        annotations_path=annotations_path,
        output_dir=annotations_path.parent,
        task_mode=mode,
        class_names=class_names,
        categories=categories,
        image_count=len(payload.get("images", []) or []),
        annotation_count=len(payload.get("annotations", []) or []),
    )


def _build_state(path: Path, annotations_path: Path) -> Optional[OutputState]:
    try:
        loaded = load_annotation_state(annotations_path)
    except Exception:
        return None
    index, created_at = _parse_state_name(path.name)
    return OutputState(
        path=path,
        annotations_path=annotations_path,
        index=index,
        created_at=created_at,
        task_mode=loaded.task_mode,
        class_names=loaded.class_names,
        image_count=loaded.image_count,
        annotation_count=loaded.annotation_count,
    )


def _parse_mode(value) -> Optional[AnnotationTaskMode]:
    if not value:
        return None
    try:
        return AnnotationTaskMode(str(value))
    except ValueError:
        return None


def _parse_state_name(name: str) -> tuple[int, Optional[datetime]]:
    match = STATE_PATTERN.match(name)
    if not match:
        return 0, None
    try:
        created_at = datetime.strptime(match.group("stamp"), "%Y%m%d_%H%M%S")
    except ValueError:
        created_at = None
    return int(match.group("index")), created_at


def _next_index(outputs_dir: Path, *, prefix: str) -> int:
    indexes = []
    for child in Path(outputs_dir).iterdir() if Path(outputs_dir).exists() else []:
        if not child.is_dir() or not child.name.startswith(prefix):
            continue
        match = re.match(rf"^{re.escape(prefix)}(?P<index>\d+)_", child.name)
        if match:
            indexes.append(int(match.group("index")))
    return max(indexes, default=0) + 1
