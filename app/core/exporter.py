"""Export primitives shared by API routes and future non-UI callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import uuid4


ExportStatus = Literal["running", "done", "error"]


@dataclass
class ExportJob:
    destination: Path
    name: str
    formats: list[str]
    use_split: bool = True
    split_ratios: tuple[float, float, float] = (0.7, 0.2, 0.1)
    progress: float = 0.0
    current_file: str = ""
    status: ExportStatus = "running"
    export_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def output_path(self) -> Path:
        return self.destination / self.name


def normalize_split(split: dict[str, float] | None) -> dict[str, float]:
    values = split or {"train": 0.7, "val": 0.2, "test": 0.1}
    total = sum(float(values.get(key, 0.0)) for key in ("train", "val", "test"))
    if abs(total - 1.0) > 0.001:
        raise ValueError("A soma de train/val/test deve ser 1.0.")
    return {key: float(values[key]) for key in ("train", "val", "test")}
