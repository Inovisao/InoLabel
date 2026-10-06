"""Casos de uso das anotações: criar, editar, apagar, marcar negativo e consultar.

Não conhece HTTP: regras recusadas viram DomainError (ver app.api.common.errors)."""

from __future__ import annotations

from typing import List

from app.api import state as _state
from app.api.annotations import mode_rules
from app.api.annotations.labels import load_labels_from_txt, reset_label_dir_cache
from app.api.annotations.persistence import autosave
from app.api.annotations.project_state import frame_dims, save_project_state
from app.api.annotations.schemas import (
    AnnotationPatch,
    AnnotationUpsert,
    FrameReviewState,
    NextTrackId,
    ReviewedUpdate,
)
from app.api.common.errors import BadRequest, InvalidInput, NotFound
from app.api.common.schemas import Annotation


def reset_annotations() -> None:
    _state.annotation_store.clear()
    _state.next_ann_id[0] = 1
    _state.reviewed_frames.clear()
    _state.coco_image_ids.clear()
    reset_label_dir_cache()


def ensure_loaded_from_disk(image_id: int) -> None:
    """Carrega do disco as anotações do frame antes da primeira mutação.

    Sem isso, anotar um frame ainda não exibido (API direta, inferência em lote)
    regravava o label só com a anotação nova e apagava as que já estavam salvas.
    """
    if image_id in _state.loaded_from_disk or image_id in _state.annotation_store:
        return
    if image_id < 0 or image_id >= len(_state.frame_paths):
        return
    dims = frame_dims(image_id)
    if dims is None:
        return
    _state.loaded_from_disk.add(image_id)
    session = _state.active_session()
    if session is not None:
        load_labels_from_txt(image_id, _state.frame_paths[image_id], dims[0], dims[1], session.output_path)


def debug_store() -> dict:
    """Development helper — returns raw annotation_store contents."""
    return {
        "total_frames_with_annotations": len(_state.annotation_store),
        "frame_indices": list(_state.annotation_store.keys()),
        "counts": {k: len(v) for k, v in _state.annotation_store.items()},
        "next_id": _state.next_ann_id[0],
    }


def next_track_id() -> NextTrackId:
    """Próximo ID livre no projeto (maior track_id usado + 1)."""
    used = [
        int(ann.track_id)
        for anns in _state.annotation_store.values() for ann in anns
        if getattr(ann, "track_id", None) is not None
    ]
    return NextTrackId(next_track_id=max(used, default=0) + 1)


def get_annotations(image_id: int) -> List[Annotation]:
    return _state.annotation_store.get(image_id, [])


def add_annotation(image_id: int, body: AnnotationUpsert) -> Annotation:
    session = _require_session()
    mode_rules.check_new(session, body)
    # frame_paths quando a sessão já carregou os frames; senão, o total declarado.
    total = len(_state.frame_paths) or session.total_frames
    if total and image_id >= total:
        raise BadRequest(f"image_id {image_id} fora do intervalo (sessão tem {total} frames, índices 0–{total - 1}).")
    bbox, obb, keypoints = mode_rules.geometry_for_new(session, body, frame_dims(image_id))

    ensure_loaded_from_disk(image_id)
    ann = Annotation(
        id=_state.next_ann_id[0],
        image_id=image_id,
        category_id=body.category_id,
        bbox=bbox,
        obb=obb,
        track_id=body.track_id,
        source=body.source,
        score=body.score,
        keypoints=keypoints,
    )
    _state.annotation_store.setdefault(image_id, []).append(ann)
    _state.next_ann_id[0] += 1
    autosave(image_id)
    return ann


def set_reviewed(image_id: int, body: ReviewedUpdate) -> FrameReviewState:
    """Marca (ou desmarca) a imagem como revisada sem objetos: vira negativo no dataset."""
    session = _state.active_session()
    if session is None:
        raise NotFound("Sessao ativa nao encontrada.")
    if session.mode == "classification":
        raise InvalidInput("Classificacao nao usa revisao de negativos.")
    if image_id < 0 or image_id >= len(_state.frame_paths):
        raise BadRequest("Index out of range.")
    if frame_dims(image_id) is None:
        raise NotFound("Imagem ilegivel.")
    if body.reviewed:
        _state.reviewed_frames.add(image_id)
    else:
        _state.reviewed_frames.discard(image_id)
    save_project_state()
    return FrameReviewState(
        image_id=image_id,
        reviewed=image_id in _state.reviewed_frames,
        annotation_count=len(_state.annotation_store.get(image_id, [])),
    )


def update_annotation(image_id: int, ann_id: int, body: AnnotationPatch) -> Annotation:
    """Altera classe, ID de rastreamento ou geometria de uma anotação existente."""
    session = _require_session()
    anns = _state.annotation_store.get(image_id, [])
    pos = next((i for i, a in enumerate(anns) if a.id == ann_id), None)
    if pos is None:
        raise NotFound("Annotation not found.")
    changes = body.model_dump(exclude_unset=True)
    mode_rules.check_patch(session, changes)
    changes = mode_rules.coherent_patch(session, anns[pos], changes, frame_dims(image_id))
    anns[pos] = anns[pos].model_copy(update=changes)
    autosave(image_id)
    return anns[pos]


def delete_annotation(image_id: int, ann_id: int) -> dict:
    anns = _state.annotation_store.get(image_id, [])
    before = len(anns)
    _state.annotation_store[image_id] = [a for a in anns if a.id != ann_id]
    if len(_state.annotation_store[image_id]) == before:
        raise NotFound("Annotation not found.")
    autosave(image_id)
    return {"ok": True}


def clear_annotations(image_id: int) -> dict:
    _state.annotation_store.pop(image_id, None)
    autosave(image_id)
    return {"ok": True}


def _require_session():
    session = _state.active_session()
    if session is None:
        raise NotFound("Sessao ativa nao encontrada.")
    return session
