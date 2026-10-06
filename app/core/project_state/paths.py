"""Onde fica o estado do projeto e como as imagens são nomeadas nele."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

STATE_SUBDIR = "saved_data_states"


_STATE_FILE_BY_MODE = {
    "obb": "annotations_obb.coco.json",
    "keypoint": "annotations_keypoints.coco.json",   # mesmo nome da 1.0.0
}


DEFAULT_STATE_FILE = "annotations.coco.json"


def state_path(output_path: Path, mode: str) -> Path:
    return Path(output_path) / STATE_SUBDIR / _STATE_FILE_BY_MODE.get(mode, DEFAULT_STATE_FILE)


def relative_name(frame_path: Path, data_path: Optional[Path]) -> str:
    """Caminho da imagem relativo ao dataset (``lote_a/img.jpg``), ou só o nome."""
    frame_path = Path(frame_path)
    if data_path is not None:
        try:
            return frame_path.relative_to(Path(data_path)).as_posix()
        except ValueError:
            pass
    return frame_path.name
