"""Estado do projeto em memória ⇄ annotations.coco.json (carregar ao abrir, regravar a cada mudança)."""

from __future__ import annotations

import logging

from app.annotation.infrastructure.persistence.state_file import read_annotation_state
from app.api import state as _state
from app.api.annotations.labels import load_labels_from_txt
from app.api.annotations.obb import finalize_obb
from app.api.common.schemas import Annotation, OBBGeometry
from app.core.project_state.builder import build_payload
from app.core.project_state.parser import parse_payload
from app.core.project_state.paths import state_path
from app.core.label_paths import find_label_file

log = logging.getLogger(__name__)


def frame_dims(image_id: int):
    """(largura, altura) do frame; lê só o cabeçalho da imagem se ainda não conhecido."""
    dims = _state.frame_dims.get(image_id)
    if dims is not None:
        return dims
    if image_id < 0 or image_id >= len(_state.frame_paths):
        return None
    try:
        from PIL import Image as _PIL

        with _PIL.open(_state.frame_paths[image_id]) as im:
            dims = im.size
    except Exception:
        return None
    _state.frame_dims[image_id] = dims
    return dims


def save_project_state() -> None:
    """Regrava o annotations.coco.json do projeto (em segundo plano)."""
    session = _state.active_session()
    if session is None or session.mode == "classification":
        return
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
        image_ids=_state.coco_image_ids,
        current_index=session.current_frame,
        keypoint_specs=session.keypoint_specs,
    )
    _state.coco_writer.submit(state_path(session.output_path, session.mode), payload)


def bootstrap_project_state() -> set:
    """Carrega o projeto inteiro ao abrir; devolve os frames que já estão em memória.

    O COCO é a fonte da verdade. Sem ele (projeto anterior a esta versão), as
    anotações vêm dos .txt e o COCO é gerado na hora, migrando o projeto.
    """
    session = _state.active_session()
    if session is None or session.mode == "classification" or not _state.frame_paths:
        return set()
    data = read_annotation_state(state_path(session.output_path, session.mode))
    if data is not None:
        parsed = parse_payload(
            data, frame_paths=_state.frame_paths, data_path=session.data_path,
            num_classes=len(session.classes),
        )
        for idx, entries in parsed.annotations.items():
            _state.annotation_store[idx] = [annotation_from_state(e) for e in entries]
        _state.frame_dims.update(parsed.dims)
        _state.reviewed_frames.update(parsed.reviewed)
        _state.coco_image_ids.update(parsed.image_ids)
        _state.next_ann_id[0] = max(_state.next_ann_id[0], parsed.max_annotation_id + 1)
        if parsed.unmatched_images or parsed.skipped_annotations:
            log.warning(
                "estado do projeto: %d imagem(ns) sem correspondente no dataset, %d anotação(ões) ignorada(s)",
                parsed.unmatched_images, parsed.skipped_annotations,
            )
        return set(range(len(_state.frame_paths)))

    if session.mode == "keypoint":
        # Keypoint é novo nesta versão: o .txt de pose é só espelho, nunca fonte.
        return set(range(len(_state.frame_paths)))

    # Migração: lê os .txt existentes e grava o COCO pela primeira vez.
    ambiguous = _state.ambiguous_frame_stems()
    migrated = False
    for idx, frame_path in enumerate(_state.frame_paths):
        if find_label_file(session.output_path, frame_path, session.data_path, ambiguous) is None:
            continue
        dims = frame_dims(idx)
        if dims is None:
            continue
        load_labels_from_txt(idx, frame_path, dims[0], dims[1], session.output_path)
        migrated = migrated or bool(_state.annotation_store.get(idx))
    if migrated:
        save_project_state()
    return set(range(len(_state.frame_paths)))


def annotation_from_state(entry: dict) -> Annotation:
    obb = entry.get("obb")
    geometry = None
    bbox = entry["bbox"]
    if isinstance(obb, dict):
        # Os cantos gravados são o que foi exportado: são a verdade se divergirem do ângulo.
        geometry, bbox = finalize_obb(OBBGeometry(**obb))
    return Annotation(
        id=entry["id"],
        image_id=entry["image_id"],
        category_id=entry["category_id"],
        bbox=bbox,
        obb=geometry,
        track_id=entry.get("track_id"),
        source=entry.get("source") or "manual",
        score=entry.get("score"),
        keypoints=entry.get("keypoints"),
    )
