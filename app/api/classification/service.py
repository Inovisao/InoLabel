"""Modo classificação: classificar, reclassificar (move, nunca duplica), consultar e desfazer."""

from __future__ import annotations

from pathlib import Path

from app.api import state as _state
from app.api.classification.schemas import ClassificationResult, ClassificationUpsert
from app.api.classification.schemas import ClassificationState as ClassificationStateResponse
from app.api.common.errors import BadRequest, InvalidInput, NotFound
from app.classification.dataset import (
    STATE_FILE_NAME,
    add_class_directory,
    load_state,
    prepare_dataset,
    reclassify_record,
    transfer_image_to_class,
    undo_record,
    write_state,
)


def _classification_context(session):
    """(arquivo de estado, registros, pastas por classe) da sessão de classificação."""
    state_file = session.output_path / STATE_FILE_NAME
    records: list = []
    class_directories = prepare_dataset(session.output_path, session.classes)
    if state_file.exists():
        try:
            loaded = load_state(state_file)
        except ValueError as exc:
            raise InvalidInput(str(exc)) from exc
        if loaded is not None:
            records = list(loaded.records)
            class_directories.update(loaded.class_directories)
    for name in session.classes:
        if name not in class_directories:
            add_class_directory(session.output_path, name, class_directories)
    return state_file, records, class_directories


def _record_index(records: list, image_path: Path):
    """Posição do último registro desta imagem (a classificação vigente), ou None."""
    target = Path(image_path).resolve()
    for pos in range(len(records) - 1, -1, -1):
        if Path(records[pos].source_path).resolve() == target:
            return pos
    return None


def _write_classification(session, state_file, records, class_directories) -> None:
    write_state(
        state_file,
        classes=session.classes,
        class_directories=class_directories,
        source_root=session.data_path,
        records=records,
    )
    session.saved_frames = len(records)
    session.annotation_count = len(records)


def _require_classification_frame(image_id: int):
    session = _state.active_session()
    if session is None:
        raise NotFound("Sessao ativa nao encontrada.")
    if session.mode != "classification":
        raise InvalidInput("Endpoint disponivel apenas no modo classificacao.")
    if not _state.frame_paths:
        raise NotFound("No frames loaded. Call /frames/init first.")
    if image_id < 0 or image_id >= len(_state.frame_paths):
        raise BadRequest("Index out of range.")
    return session


_classification_cache: dict = {"key": None, "by_source": {}}


def current_classification_id(image_path: Path):
    """Índice da classe já atribuída à imagem, lido do estado (cacheado pelo mtime)."""
    session = _state.active_session()
    if session is None or session.mode != "classification":
        return None
    state_file = session.output_path / STATE_FILE_NAME
    try:
        key = (str(state_file), state_file.stat().st_mtime_ns)
    except OSError:
        return None
    if _classification_cache["key"] != key:
        by_source: dict = {}
        try:
            loaded = load_state(state_file)
        except ValueError:
            loaded = None
        for record in (loaded.records if loaded is not None else ()):
            by_source[str(Path(record.source_path).resolve())] = record.class_name
        _classification_cache.update(key=key, by_source=by_source)
    name = _classification_cache["by_source"].get(str(Path(image_path).resolve()))
    return session.classes.index(name) if name in session.classes else None


def classify_frame(image_id: int, body: ClassificationUpsert) -> ClassificationResult:
    """Classifica a imagem. Se ela já tinha classe, troca de pasta em vez de duplicar."""
    session = _require_classification_frame(image_id)
    if body.category_id >= len(session.classes):
        raise InvalidInput("category_id fora do intervalo de classes.")
    class_name = session.classes[body.category_id]
    state_file, records, class_directories = _classification_context(session)
    image_path = _state.frame_paths[image_id]

    pos = _record_index(records, image_path)
    if pos is not None:
        record = reclassify_record(
            records[pos], class_name=class_name,
            output_dir=session.output_path, class_directories=class_directories,
        )
        records[pos] = record
    else:
        record = transfer_image_to_class(
            image_path, class_name=class_name, output_dir=session.output_path,
            class_directories=class_directories, move=body.move_file,
        )
        records.append(record)
    _write_classification(session, state_file, records, class_directories)

    return ClassificationResult(
        image_id=image_id,
        filename=image_path.name,
        top1_class_id=body.category_id,
        top1_class_name=class_name,
        destination_path=str(record.destination_path),
        operation=record.operation,
    )


def get_classification(image_id: int) -> ClassificationStateResponse:
    session = _require_classification_frame(image_id)
    class_id = current_classification_id(_state.frame_paths[image_id])
    return ClassificationStateResponse(
        image_id=image_id, class_id=class_id,
        class_name=session.classes[class_id] if class_id is not None else None,
    )


def undo_classification(image_id: int) -> ClassificationStateResponse:
    """Desfaz a classificação: apaga a cópia (ou devolve a imagem movida) e o registro."""
    session = _require_classification_frame(image_id)
    state_file, records, class_directories = _classification_context(session)
    pos = _record_index(records, _state.frame_paths[image_id])
    if pos is None:
        raise NotFound("Imagem ainda nao classificada.")
    undo_record(records.pop(pos))
    _write_classification(session, state_file, records, class_directories)
    return ClassificationStateResponse(image_id=image_id)
