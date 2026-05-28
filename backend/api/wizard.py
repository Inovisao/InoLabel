"""Endpoints do wizard de inicializacao."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_dialog_executor = ThreadPoolExecutor(max_workers=1)

from backend.core.session import AnnotationTaskMode
from backend.core.output_state import (
    list_output_states,
    list_output_states_for_sources,
    load_annotation_state,
    find_annotations_path,
)
from backend.core.startup_cache import load_startup_cache, save_startup_cache

router = APIRouter(prefix="/api/wizard", tags=["wizard"])


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/modes")
async def list_modes():
    """Lista os modos de anotacao disponiveis."""
    return [
        {"value": m.value, "label": m.label}
        for m in AnnotationTaskMode
    ]


@router.post("/validate-path")
async def validate_path(path: str, kind: str = "dataset"):
    """Valida se um caminho de dataset ou modelo existe."""
    p = Path(path).expanduser()
    exists = p.exists()
    is_dir = p.is_dir() if exists else False
    is_file = p.is_file() if exists else False
    return {
        "path": str(p),
        "exists": exists,
        "is_dir": is_dir,
        "is_file": is_file,
    }


@router.get("/startup-cache")
async def get_startup_cache():
    """Carrega o cache da ultima sessao do usuario."""
    return load_startup_cache()


class SaveCacheRequest(BaseModel):
    data: Dict[str, Any]


@router.post("/startup-cache")
async def save_cache(req: SaveCacheRequest):
    """Salva o cache de configuracao para proxima sessao."""
    save_startup_cache(req.data)
    return {"saved": True}


def _open_folder_dialog_sync() -> str:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    path = filedialog.askdirectory(parent=root, title="Selecionar pasta do dataset")
    root.destroy()
    return path or ""


@router.get("/browse-folder")
async def browse_folder():
    """Abre o dialogo nativo de selecao de pasta e retorna o caminho escolhido."""
    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(_dialog_executor, _open_folder_dialog_sync)
    return {"path": path}


def _open_file_dialog_sync(title: str, filetypes: list) -> str:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    path = filedialog.askopenfilename(parent=root, title=title, filetypes=filetypes)
    root.destroy()
    return path or ""


@router.get("/browse-file")
async def browse_file(kind: str = "coco"):
    """Abre o dialogo nativo de selecao de arquivo e retorna o caminho escolhido."""
    if kind == "coco":
        title = "Selecionar arquivo COCO JSON"
        filetypes = [("COCO JSON", "*.json"), ("Todos os arquivos", "*.*")]
    else:
        title = "Selecionar arquivo"
        filetypes = [("Todos os arquivos", "*.*")]
    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(_dialog_executor, _open_file_dialog_sync, title, filetypes)
    return {"path": path}


@router.get("/output-states")
async def get_output_states(data_root: Optional[str] = None):
    """Lista sessoes de anotacao existentes, opcionalmente filtradas pela origem de dados."""
    if data_root:
        sources = [Path(data_root).expanduser()]
        states = list_output_states_for_sources(sources)
    else:
        states = list_output_states()

    return [
        {
            "path": str(s.path),
            "annotations_path": str(s.annotations_path),
            "label": s.label,
            "task_mode": s.task_mode.value if s.task_mode else None,
            "class_names": list(s.class_names),
            "image_count": s.image_count,
            "annotation_count": s.annotation_count,
            "modified_at": s.modified_at.isoformat() if s.modified_at else None,
        }
        for s in states
    ]


@router.get("/load-annotations")
async def load_annotations_info(path: str):
    """Carrega metadados de um arquivo de anotacoes existente."""
    p = Path(path).expanduser()
    try:
        state = load_annotation_state(p)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc))

    return {
        "task_mode": state.task_mode.value if state.task_mode else None,
        "class_names": list(state.class_names),
        "categories": [dict(c) for c in state.categories],
        "image_count": state.image_count,
        "annotation_count": state.annotation_count,
        "output_dir": str(state.output_dir),
        "annotations_path": str(state.annotations_path),
    }
