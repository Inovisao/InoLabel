"""Manifesto do projeto (.inolabel.json): lido ao abrir, gravado ao abrir e ao fechar.

A página de Projetos e o workspace usam este arquivo para listar e retomar projetos.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

META_FILE = ".inolabel.json"


def read(output_path: Path) -> dict:
    """Conteúdo do manifesto, ou {} se não existir ou estiver ilegível."""
    path = Path(output_path) / META_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_on_start(session, existing: dict, keypoint_specs: list) -> None:
    """Preserva o que o workspace gravou (nome, versão, created_at) e atualiza a sessão."""
    meta = {
        **existing,
        "session_id": session.session_id,
        "mode": session.mode,
        "data_path": str(session.data_path),
        "classes": session.classes,
        "current_frame": session.current_frame,
        "created_at": existing.get("created_at") or _now(),
    }
    if keypoint_specs:
        meta["keypoint_classes"] = [{"name": name, **spec} for name, spec in zip(session.classes, keypoint_specs)]
    _write(session.output_path, meta)


def update_on_stop(session) -> None:
    """Dados frescos para a página de Projetos (frame atual, última modificação)."""
    meta = read(session.output_path)
    meta.update({
        "mode": session.mode,
        "classes": session.classes,
        "data_path": str(session.data_path),
        "last_modified": _now(),
        "current_frame": session.current_frame,
    })
    _write(session.output_path, meta)


def _write(output_path: Path, meta: dict) -> None:
    # Falhar aqui não impede anotar: a página de Projetos só não verá a sessão.
    try:
        (Path(output_path) / META_FILE).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
