"""Workspace de projetos, no modelo dos vaults do Obsidian.

O usuário escolhe uma pasta (o workspace); cada projeto é uma subpasta dela com o
seu ``.inolabel.json``. Um índice em ``<workspace>/.inolabel/workspace.json`` guarda
nome e lista de projetos — se ele sumir ou divergir, é reconstruído varrendo as
subpastas. A lista de workspaces recentes fica no app (``LOCAL_DIR``), não no
navegador, para não se perder ao trocar de navegador.

Substitui a pasta de saída em texto livre, que, relativa, ia parar dentro da pasta
de onde o app foi aberto.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.coco_state_writer import write_json_atomic

WORKSPACE_DIR = ".inolabel"
INDEX_FILE = "workspace.json"
PROJECT_META = ".inolabel.json"
RECENTS_FILE = "workspaces.json"
MAX_RECENTS = 10

_WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
_FORBIDDEN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class WorkspaceError(ValueError):
    """Pedido inválido sobre o workspace (nome, pasta inexistente, projeto repetido)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_project_name(name: str) -> str:
    """Nome de pasta válido em Linux, macOS e Windows; erro com o motivo caso contrário."""
    clean = str(name or "").strip()
    if not clean:
        raise WorkspaceError("Informe um nome para o projeto.")
    if clean in (".", "..") or _FORBIDDEN_CHARS.search(clean):
        raise WorkspaceError('O nome não pode conter / \\ : * ? " < > | nem ser "." ou "..".')
    if clean.endswith((".", " ")):
        raise WorkspaceError("O nome não pode terminar com ponto ou espaço.")
    if clean.split(".")[0].lower() in _WINDOWS_RESERVED:
        raise WorkspaceError(f"'{clean}' é um nome reservado no Windows.")
    if len(clean) > 100:
        raise WorkspaceError("O nome pode ter no máximo 100 caracteres.")
    return clean


def index_path(root: Path) -> Path:
    return Path(root) / WORKSPACE_DIR / INDEX_FILE


def _require_absolute_dir(root: Path) -> Path:
    root = Path(root).expanduser()
    if not root.is_absolute():
        raise WorkspaceError("Informe o caminho completo da pasta do workspace.")
    return root.resolve()


def _scan_projects(root: Path) -> List[dict]:
    projects = []
    for child in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        meta_file = child / PROJECT_META
        if not meta_file.is_file():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        projects.append({
            "folder": child.name,
            "name": meta.get("name") or child.name,
            "mode": meta.get("mode", ""),
            "created_at": meta.get("created_at", ""),
        })
    return projects


def load_workspace(root: Path) -> dict:
    """Abre um workspace existente; reconstrói o índice se ele faltar ou estiver ilegível."""
    root = _require_absolute_dir(root)
    if not root.is_dir():
        raise WorkspaceError(f"A pasta do workspace não existe: {root}")
    index: Optional[dict] = None
    try:
        index = json.loads(index_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        index = None
    if not isinstance(index, dict):
        index = {"version": 1, "name": root.name, "created_at": _now()}
    # O índice é sempre conferido com o disco: projetos copiados para dentro da
    # pasta aparecem, pastas apagadas somem.
    index["projects"] = _scan_projects(root)
    write_json_atomic(index_path(root), index)
    return {**index, "path": str(root)}


def create_workspace(root: Path, name: Optional[str] = None) -> dict:
    """Cria (ou adota) a pasta como workspace. Não mexe em projetos que já estejam nela."""
    root = _require_absolute_dir(root)
    root.mkdir(parents=True, exist_ok=True)
    if not index_path(root).is_file():
        write_json_atomic(index_path(root), {"version": 1, "name": name or root.name, "created_at": _now(), "projects": []})
    return load_workspace(root)


def create_project(root: Path, *, name: str, mode: str, data_path: Path, classes: List[str]) -> Path:
    """Cria a pasta do projeto dentro do workspace com o manifesto ``.inolabel.json``."""
    root = _require_absolute_dir(root)
    folder = validate_project_name(name)
    project = root / folder
    if project.exists():
        raise WorkspaceError(f"Já existe um projeto chamado '{folder}' neste workspace.")
    data_path = Path(data_path).expanduser()
    if not data_path.is_absolute() or not data_path.exists():
        raise WorkspaceError(f"Dataset não encontrado: {data_path}")
    project.mkdir(parents=True)
    write_json_atomic(project / PROJECT_META, {
        "version": 1,
        "name": folder,
        "mode": mode,
        "data_path": str(data_path.resolve()),
        "classes": list(classes),
        "current_frame": 0,
        "created_at": _now(),
    })
    load_workspace(root)
    return project


def update_project(root: Path, folder: str, *, data_path: Optional[Path] = None) -> dict:
    """Atualiza o manifesto do projeto (ex.: apontar o novo lugar do dataset)."""
    root = _require_absolute_dir(root)
    meta_file = root / validate_project_name(folder) / PROJECT_META
    if not meta_file.is_file():
        raise WorkspaceError(f"Projeto não encontrado: {folder}")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    if data_path is not None:
        data_path = Path(data_path).expanduser()
        if not data_path.is_absolute() or not data_path.exists():
            raise WorkspaceError(f"Dataset não encontrado: {data_path}")
        meta["data_path"] = str(data_path.resolve())
    write_json_atomic(meta_file, meta)
    return meta


# ── workspaces recentes (no app, não no navegador) ───────────────────────────

def load_recents(local_dir: Path) -> List[dict]:
    try:
        data = json.loads((Path(local_dir) / RECENTS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("recent", []) if isinstance(data, dict) else []
    return [i for i in items if isinstance(i, dict) and i.get("path")]


def remember_workspace(local_dir: Path, workspace: dict) -> List[dict]:
    entry = {"path": workspace["path"], "name": workspace.get("name") or Path(workspace["path"]).name, "opened_at": _now()}
    recents = [entry] + [r for r in load_recents(local_dir) if r["path"] != entry["path"]]
    recents = recents[:MAX_RECENTS]
    write_json_atomic(Path(local_dir) / RECENTS_FILE, {"version": 1, "recent": recents})
    return recents
