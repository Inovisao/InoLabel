"""Monta o COCO a exportar a partir do projeto em memória (o mesmo do annotations.coco.json)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.api import state as _state
from app.api.annotations.labels import load_labels_from_txt
from app.api.annotations.project_state import frame_dims
from app.core.project_state.builder import build_payload
from app.core.project_state.paths import relative_name
from app.core.label_paths import find_label_file


@dataclass
class ExportPayload:
    payload: dict
    # file_name (relativo ao dataset) → imagem original, copiada sem passo intermediário.
    source_image_map: dict[str, Path]

    @property
    def images(self) -> list[dict]:
        return self.payload["images"]


def collect(session) -> ExportPayload:
    """Categorias a partir de 1, file_name relativo (preserva subpastas) e negativos marcados."""
    _load_unvisited_labels(session)
    for idx in set(_state.annotation_store) | _state.reviewed_frames:
        frame_dims(idx)
    payload = build_payload(
        mode=session.mode,
        classes=session.classes,
        data_path=session.data_path,
        frame_paths=_state.frame_paths,
        frame_dims=_state.frame_dims,
        annotation_store=_state.annotation_store,
        reviewed=_state.reviewed_frames,
        image_ids=dict(_state.coco_image_ids),
        keypoint_specs=session.keypoint_specs,
    )
    by_name = {relative_name(p, session.data_path): p for p in _state.frame_paths}
    source_image_map = {img["file_name"]: by_name[img["file_name"]] for img in payload["images"]}
    return ExportPayload(payload=payload, source_image_map=source_image_map)


def _load_unvisited_labels(session) -> None:
    """Traz para a memória os .txt de frames ainda não abertos nesta sessão.

    Parte de cada imagem para o seu label. O caminho inverso (do .txt para "a imagem
    com aquele stem") atribuía o label à imagem errada quando o nome se repetia em
    subpastas.
    """
    if not (session.output_path / "labels").exists():
        return
    ambiguous = _state.ambiguous_frame_stems()
    for frame_idx, frame_path in enumerate(_state.frame_paths):
        if frame_idx in _state.annotation_store:
            continue
        if find_label_file(session.output_path, frame_path, session.data_path, ambiguous) is None:
            continue
        dims = frame_dims(frame_idx)
        if dims is None:
            continue
        load_labels_from_txt(frame_idx, frame_path, dims[0], dims[1], session.output_path)
