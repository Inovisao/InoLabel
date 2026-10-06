"""Registros da classificação: cada imagem classificada e o estado salvo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


STATE_FILE_NAME = "classification_state.json"


@dataclass(frozen=True)
class ClassificationRecord:
    source_path: Path
    destination_path: Path
    class_name: str
    classified_at: str
    operation: str = "copy"


@dataclass(frozen=True)
class ClassificationState:
    classes: tuple[str, ...]
    class_directories: dict[str, str]
    source_root: Path
    records: tuple[ClassificationRecord, ...]

    @property
    def classified_sources(self) -> set[Path]:
        return {record.source_path for record in self.records}


@dataclass(frozen=True)
class ClassificationOutputState:
    path: Path
    state_path: Path
    index: int
    created_at: Optional[datetime]
    modified_at: Optional[datetime]
    class_names: tuple[str, ...]
    image_count: int
    source_root: Path

    @property
    def label(self) -> str:
        stamp_source = self.modified_at or self.created_at
        stamp = stamp_source.strftime("%d/%m/%Y %H:%M:%S") if stamp_source else self.path.name
        return f"{self.path.name} | {stamp} | classificacao | {len(self.class_names)} classes | {self.image_count} imagens"
