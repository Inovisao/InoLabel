"""Rotas HTTP do seletor de pasta/arquivo do sistema."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.api.browse.native_dialog import pick_file, pick_folder

router = APIRouter(prefix="/api/browse", tags=["browse"])


@router.get("/folder")
async def browse_folder() -> dict:
    # O diálogo bloqueia até o usuário escolher: fora da thread do servidor.
    return {"path": await run_in_threadpool(pick_folder)}


@router.get("/file")
async def browse_file(ext: str = "") -> dict:
    filetypes = (
        [("Modelo YOLO", "*.pt"), ("Todos os arquivos", "*.*")]
        if ext == "pt"
        else [("Todos os arquivos", "*.*")]
    )
    return {"path": await run_in_threadpool(pick_file, filetypes)}
