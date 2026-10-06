"""Sessão de anotação: abrir (validando tudo antes), consultar, agir e encerrar."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.annotation.infrastructure.persistence.state_file import AnnotationStateUnreadableError, read_annotation_state
from app.api import state as _state
from app.api.annotations.service import reset_annotations
from app.api.common.errors import InvalidInput, NotFound
from app.api.session import project_meta
from app.api.session.keypoint_specs import resolve_keypoint_specs
from app.api.session.schemas import (
    SessionActionRequest,
    SessionActionResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStatusResponse,
    SessionStopResponse,
)
from app.api.state import active_session, create_session, get_session, remove_session
from app.config import IMAGE_EXTENSIONS, IMAGE_LIST_EXTENSIONS, OUTPUT_BASE, VIDEO_EXTENSIONS
from app.core.project_state.paths import state_path

log = logging.getLogger(__name__)


@dataclass
class _StartPlan:
    """Tudo o que o pedido de início precisa, já validado (nada foi alterado ainda)."""

    data_path: Path
    output_path: Path
    model_path: Optional[Path]
    project_state: Optional[Path]   # annotations*.coco.json (None na classificação)
    keypoint_specs: list


def start_session(req: SessionStartRequest) -> SessionStartResponse:
    """Abre a sessão: valida tudo, só então encerra a sessão ativa e cria a nova.

    A ordem importa: um pedido inválido não pode derrubar a sessão em andamento sem
    abrir outra no lugar.
    """
    plan = _validate(req)
    _stop_active_session()
    _prepare_output_dir(plan.output_path)
    reset_annotations()

    # Lido antes de gravar: frame para retomar e created_at a preservar.
    existing_meta = project_meta.read(plan.output_path)
    total = count_frames(plan.data_path)
    if plan.project_state is not None:
        _backup(plan.project_state)

    session = create_session(
        mode=req.mode.value,
        data_path=plan.data_path,
        output_path=plan.output_path,
        model_path=plan.model_path,
        resume=req.resume,
        classes=req.classes,
        total_frames=total,
        current_frame=_restored_frame(req, existing_meta, total),
        keypoint_specs=plan.keypoint_specs,
    )
    log.info(
        "start_session: created session %s mode=%s frames=%d path=%s resume=%s frame=%d",
        session.session_id, session.mode, total, plan.data_path, req.resume, session.current_frame,
    )
    # Para a página de Projetos achar a sessão depois.
    project_meta.write_on_start(session, existing_meta, plan.keypoint_specs)

    return SessionStartResponse(
        session_id=session.session_id,
        total_frames=session.total_frames,
        current_frame=session.current_frame,
        mode=req.mode,
        current_index=session.current_frame,
        classes=session.classes,
    )


def _validate(req: SessionStartRequest) -> _StartPlan:
    if req.data_path is None:
        raise InvalidInput("Informe data_path.")
    data_path = Path(req.data_path).expanduser().resolve()
    if not data_path.exists():
        raise InvalidInput(f"Dataset não encontrado: {data_path}")

    # Caminho relativo seria resolvido a partir da pasta onde o app foi aberto: com
    # "python main.py" na raiz do repositório, o projeto ia parar dentro do repositório.
    if req.output_path and not Path(req.output_path).expanduser().is_absolute():
        raise InvalidInput(
            f"Informe o caminho completo da pasta de saída (recebido: '{req.output_path}'). "
            "Use o botão de selecionar pasta."
        )
    output_path = (Path(req.output_path).expanduser() if req.output_path else OUTPUT_BASE).resolve()

    model_path: Optional[Path] = None
    if req.model_path:
        model_path = Path(req.model_path).expanduser().resolve()
        if not model_path.exists():
            raise InvalidInput(f"Modelo não encontrado: {model_path}")
        if model_path.suffix.lower() != ".pt":
            raise InvalidInput("Modelo deve ser um arquivo .pt válido.")

    # Estado do projeto ilegível: não abre a sessão nem toca no arquivo, para que
    # ele possa ser restaurado (.bak) ou corrigido.
    project_state = None
    project_data = None
    if req.mode.value != "classification":
        project_state = state_path(output_path, req.mode.value)
        try:
            project_data = read_annotation_state(project_state)
        except AnnotationStateUnreadableError as exc:
            raise InvalidInput(str(exc)) from exc
    keypoint_specs = (
        resolve_keypoint_specs(req, output_path, project_data) if req.mode.value == "keypoint" else []
    )
    return _StartPlan(data_path, output_path, model_path, project_state, keypoint_specs)


def _stop_active_session() -> None:
    existing = active_session()
    if existing is not None:
        log.info("start_session: auto-stopping session %s to start a new one", existing.session_id)
        remove_session(existing.session_id)
        reset_annotations()


def _prepare_output_dir(output_path: Path) -> None:
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise InvalidInput(f"Não foi possível criar a pasta de saída ({output_path}): {exc}") from exc


def _restored_frame(req: SessionStartRequest, meta: dict, total: int) -> int:
    """Ao retomar, volta ao último frame — preso ao intervalo, caso imagens tenham sumido."""
    if not req.resume:
        return 0
    try:
        return min(max(int(meta.get("current_frame", 0)), 0), max(total - 1, 0))
    except (TypeError, ValueError):
        return 0


def _backup(project_state: Path) -> None:
    """Cópia do último estado bom antes de qualquer gravação desta sessão."""
    if not project_state.is_file():
        return
    try:
        shutil.copy2(project_state, project_state.with_name(project_state.name + ".bak"))
    except OSError:
        log.warning("start_session: não foi possível criar o .bak do estado do projeto")


def count_frames(path: Path) -> int:
    """Quantidade de frames anotáveis. Pode demorar em datasets grandes (varre a árvore)."""
    if path.is_dir():
        exts = set(IMAGE_EXTENSIONS)
        return sum(1 for child in path.rglob("*") if child.is_file() and child.suffix.lower() in exts)
    if path.suffix.lower() in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + IMAGE_LIST_EXTENSIONS:
        return 1
    return 0


def status(session_id: str) -> SessionStatusResponse:
    session = get_session(session_id)
    if session is None:
        raise NotFound("Sessão não encontrada")
    return SessionStatusResponse(
        session_id=session.session_id,
        current_frame=session.current_frame,
        total_frames=session.total_frames,
        saved_frames=session.saved_frames,
        status=session.status,
    )


def active_status() -> dict:
    """Estado da sessão ativa (usado pelo frontend para reconectar após recarregar)."""
    session = active_session()
    if session is None:
        return {
            "active": False,
            "session_id": None,
            "total_frames": 0,
            "current_index": 0,
            "classes": [],
            "autosaved": False,
            "data_path": None,
            "output_path": None,
        }
    return {
        "active": True,
        "session_id": session.session_id,
        "mode": session.mode,
        "total_frames": session.total_frames,
        "current_index": session.current_frame,
        "classes": session.classes,
        "autosaved": False,
        "data_path": str(session.data_path),
        "output_path": str(session.output_path),
    }


def run_action(session_id: str, body: SessionActionRequest) -> SessionActionResponse:
    session = get_session(session_id)
    if session is None:
        raise NotFound("Sessão não encontrada")
    last = max(session.total_frames - 1, 0)
    if body.action in {"validate", "reject"}:
        session.saved_frames += 1
        session.current_frame = min(session.current_frame + 1, last)
    elif body.action == "next":
        session.current_frame = min(session.current_frame + 1, last)
    elif body.action == "prev":
        session.current_frame = max(session.current_frame - 1, 0)
    elif body.action == "undo":
        session.annotation_count = max(session.annotation_count - 1, 0)
    else:
        raise InvalidInput("Ação inválida")
    return SessionActionResponse(current_frame=session.current_frame, annotation_count=session.annotation_count)


def stop(session_id: str) -> SessionStopResponse:
    _flush_project_state()
    session = remove_session(session_id)
    if session is None:
        raise NotFound("Sessão não encontrada")
    reset_annotations()
    project_meta.update_on_stop(session)
    return SessionStopResponse(saved_frames=session.saved_frames, output_path=str(session.output_path))


def stop_active() -> dict:
    session = active_session()
    if session is None:
        return {"ok": True}
    _flush_project_state()
    remove_session(session.session_id)
    project_meta.update_on_stop(session)
    reset_annotations()
    return {"ok": True}


def _flush_project_state() -> None:
    """Conclui a gravação pendente do annotations.coco.json antes de encerrar."""
    if not _state.coco_writer.flush(timeout=60):
        log.error("estado do projeto: gravação pendente não terminou em 60 s")
