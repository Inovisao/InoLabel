"""Classes da sessão: listar e editar durante a anotação (adicionar, renomear, remover).

O ``category_id`` de cada anotação é a posição da classe em ``session.classes``.
Adicionar (no fim) e renomear não mexem em ids; remover apaga as anotações da
classe e desce 1 o id das classes depois dela, no projeto inteiro.

Não conhece HTTP: regras recusadas viram DomainError (ver app.api.common.errors)."""

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import ValidationError

from app.api import state as _state
from app.api.annotations.labels import write_label_file
from app.api.annotations.project_state import frame_dims, save_project_state
from app.api.classes.schemas import ClassCreate, ClassItem, ClassRename, ClassUsage
from app.api.common.errors import InvalidInput, NotFound
from app.api.session import project_meta
from app.api.session.schemas import KeypointClassSpec
from app.core.palette import CLASS_COLORS

log = logging.getLogger(__name__)


def list_classes() -> List[ClassItem]:
    session = _state.active_session()
    if session is None:
        return []
    specs = session.keypoint_specs or []
    return [
        ClassItem(
            id=i,
            name=name,
            color=CLASS_COLORS[i % len(CLASS_COLORS)],
            keypoints=(specs[i] if i < len(specs) else {}).get("keypoints", []),
            skeleton=(specs[i] if i < len(specs) else {}).get("skeleton", []),
        )
        for i, name in enumerate(session.classes)
    ]


def add_class(body: ClassCreate) -> List[ClassItem]:
    session = _require_session()
    name = _valid_name(session, body.name)
    spec = None
    if session.mode == "keypoint":
        try:
            spec = KeypointClassSpec(name=name, keypoints=body.keypoints)
        except ValidationError as exc:
            raise InvalidInput(str(exc.errors()[0]["msg"]).replace("Value error, ", "")) from exc
    session.classes.append(name)
    if spec is not None:
        session.keypoint_specs.append({"keypoints": list(spec.keypoints), "skeleton": []})
    if session.mode == "classification":
        from app.api.classification.service import sync_class_directories

        sync_class_directories(session)
    _persist(session, frames=[])
    return list_classes()


def rename_class(class_id: int, body: ClassRename) -> List[ClassItem]:
    session = _require_session()
    _require_class(session, class_id)
    if session.mode == "classification":
        raise InvalidInput("Na classificação, cada classe é uma pasta com imagens; renomear não está disponível.")
    session.classes[class_id] = _valid_name(session, body.name, ignore=class_id)
    # Os .txt guardam só o id; o nome está no COCO e no manifesto.
    _persist(session, frames=[])
    return list_classes()


def class_usage(class_id: int) -> ClassUsage:
    session = _require_session()
    _require_class(session, class_id)
    frames = [anns for anns in _state.annotation_store.values() if any(a.category_id == class_id for a in anns)]
    return ClassUsage(
        id=class_id,
        name=session.classes[class_id],
        annotations=sum(1 for anns in frames for a in anns if a.category_id == class_id),
        frames=len(frames),
    )


def remove_class(class_id: int) -> List[ClassItem]:
    session = _require_session()
    _require_class(session, class_id)
    if session.mode == "classification":
        raise InvalidInput("Na classificação, cada classe é uma pasta com imagens; remover não está disponível.")
    if len(session.classes) <= 1:
        raise InvalidInput("O projeto precisa de ao menos uma classe.")
    if not _state.frame_paths:
        # Sem os frames carregados o projeto não está todo na memória: ids ficariam velhos no disco.
        raise NotFound("Nenhum frame carregado. Chame /frames/init primeiro.")

    touched: List[int] = []
    removed = 0
    for idx, anns in _state.annotation_store.items():
        kept = []
        changed = False
        for ann in anns:
            if ann.category_id == class_id:
                removed += 1
                changed = True
                continue
            if ann.category_id > class_id:
                ann.category_id -= 1
                changed = True
            kept.append(ann)
        if changed:
            _state.annotation_store[idx] = kept
            touched.append(idx)

    session.classes.pop(class_id)
    if class_id < len(session.keypoint_specs):
        session.keypoint_specs.pop(class_id)
    session.annotation_count = max(0, session.annotation_count - removed)
    log.info("remove_class: classe %d removida, %d anotação(ões), %d frame(s) regravado(s)", class_id, removed, len(touched))
    _persist(session, frames=touched)
    return list_classes()


def _persist(session, frames: List[int]) -> None:
    """Regrava os .txt dos frames que mudaram, o COCO e o manifesto do projeto."""
    for idx in frames:
        dims = frame_dims(idx)
        if dims is None or not dims[0] or not dims[1]:
            log.warning("classes: frame %d sem dimensões, .txt não regravado", idx)
            continue
        write_label_file(session, idx, dims[0], dims[1])
    save_project_state()
    project_meta.update_classes(session)


def _require_session():
    session = _state.active_session()
    if session is None:
        raise NotFound("Sessão ativa não encontrada.")
    return session


def _require_class(session, class_id: int) -> None:
    if not 0 <= class_id < len(session.classes):
        raise NotFound(f"Classe {class_id} não existe.")


def _valid_name(session, raw: str, ignore: Optional[int] = None) -> str:
    name = raw.strip()
    if not name:
        raise InvalidInput("Informe o nome da classe.")
    if len(name) > 100:
        raise InvalidInput("Nome da classe muito longo (máximo 100 caracteres).")
    taken = {other.casefold() for i, other in enumerate(session.classes) if i != ignore}
    if name.casefold() in taken:
        raise InvalidInput(f"Já existe uma classe '{name}'.")
    return name
