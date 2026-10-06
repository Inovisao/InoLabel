"""Frames da sessão: varredura do dataset, navegação e montagem do frame exibido."""

from __future__ import annotations

import os
from pathlib import Path

from app.api import state as _state
from app.api.annotations.project_state import bootstrap_project_state
from app.api.annotations.service import ensure_loaded_from_disk, reset_annotations
from app.api.classification.service import current_classification_id
from app.api.common.errors import BadRequest, NotFound
from app.api.frames import image_cache
from app.api.frames.schemas import FrameResponse
from app.config import IMAGE_EXTENSIONS

_IMAGE_EXTS = set(IMAGE_EXTENSIONS)


def load_frame_paths() -> None:
    """Lista as imagens do dataset da sessão (pasta, recursivo, ou um arquivo) em ordem."""
    session = _state.active_session()
    if session is None:
        _state.frame_paths.clear()
        return
    root = session.data_path
    if root.is_dir():
        # os.walk é mais rápido que rglob("*") em árvores grandes: usa scandir e
        # não cria Path para arquivos que não são imagem.
        results: list[Path] = []
        for dirpath, _dirnames, filenames in os.walk(str(root)):
            dir_p = Path(dirpath)
            for fn in filenames:
                if Path(fn).suffix.lower() in _IMAGE_EXTS:
                    results.append(dir_p / fn)
        _state.frame_paths[:] = sorted(results)
    elif root.is_file() and root.suffix.lower() in _IMAGE_EXTS:
        _state.frame_paths[:] = [root]
    else:
        _state.frame_paths.clear()


def init_frames() -> dict:
    """Abre o dataset da sessão e sobe o projeto inteiro para a memória."""
    load_frame_paths()
    session = _state.active_session()
    start = session.current_frame if session is not None else 0
    # A quantidade de frames pode ter mudado desde a última sessão.
    _state.current_frame_index[0] = min(start, len(_state.frame_paths) - 1) if _state.frame_paths else 0
    _state.loaded_from_disk.clear()
    _state.frame_dims.clear()
    image_cache.clear()
    # O COCO de estado é montado a partir da memória: frames ainda não visitados
    # não podem sumir dele.
    reset_annotations()
    _state.loaded_from_disk.update(bootstrap_project_state())
    return {"total": len(_state.frame_paths), "current_index": _state.current_frame_index[0]}


def current_frame() -> FrameResponse:
    if not _state.frame_paths:
        raise NotFound("No frames loaded. Call /frames/init first.")
    return _response(_state.current_frame_index[0])


def next_frame() -> FrameResponse:
    _require_frames()
    return _go_to(min(_state.current_frame_index[0] + 1, len(_state.frame_paths) - 1))


def prev_frame() -> FrameResponse:
    _require_frames()
    return _go_to(max(_state.current_frame_index[0] - 1, 0))


def goto_frame(index: int) -> FrameResponse:
    _require_frames()
    if index < 0 or index >= len(_state.frame_paths):
        raise BadRequest("Index out of range.")
    return _go_to(index)


def _require_frames() -> None:
    if not _state.frame_paths:
        raise NotFound("No frames loaded.")


def _go_to(index: int) -> FrameResponse:
    _state.current_frame_index[0] = index
    # session.current_frame acompanha o índice para retomar no mesmo frame.
    session = _state.active_session()
    if session is not None:
        session.current_frame = index
    return _response(index)


def _response(index: int) -> FrameResponse:
    path = _state.frame_paths[index]
    image_b64 = image_cache.cached(index) or image_cache.encode(index)
    if image_b64 is None:
        raise NotFound(f"Cannot read {path.name}")
    # O frame pode ter vindo do pré-carregamento, que não lê as anotações.
    ensure_loaded_from_disk(index)

    anns = _state.annotation_store.get(index, [])
    classification_id = current_classification_id(path)

    # Vizinhos dos dois lados: avançar e voltar ficam instantâneos.
    image_cache.prefetch(index + 1)
    image_cache.prefetch(index - 1)

    return FrameResponse(
        index=index,
        total=len(_state.frame_paths),
        image_b64=image_b64,
        filename=path.name,
        annotations=list(anns),   # cópia: o Pydantic não pode mexer na lista compartilhada
        is_saved=bool(anns) or index in _state.reviewed_frames or classification_id is not None,
        reviewed=index in _state.reviewed_frames,
        classification_id=classification_id,
    )
