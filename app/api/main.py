"""FastAPI application for the InoLabel WebUI."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.annotations.router import router as annotations_router
from app.api.browse.router import router as browse_router
from app.api.classes.router import router as classes_router
from app.api.classification.router import router as classification_router
from app.api.common.errors import DomainError
from app.api.export.router import router as export_router
from app.api.frames.router import router as frames_router
from app.api.inference.router import router as inference_router
from app.api.keybinds.router import router as keybinds_router
from app.api.modes.router import router as modes_router
from app.api.projects.router import router as projects_router
from app.api.session.router import router as session_router
from app.api.workspace.router import router as workspace_router

app = FastAPI(title="InoLabel API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(modes_router)
app.include_router(projects_router)
app.include_router(session_router)
app.include_router(export_router)
app.include_router(inference_router)
app.include_router(keybinds_router)
app.include_router(frames_router)
# Classificação antes de anotações: DELETE /{image_id}/classification precisa vir
# antes de DELETE /{image_id}/{ann_id}.
app.include_router(classification_router)
app.include_router(annotations_router)
app.include_router(classes_router)
app.include_router(browse_router)
app.include_router(workspace_router)


@app.exception_handler(DomainError)
async def _domain_error(_request: Request, exc: DomainError) -> JSONResponse:
    """Regra de negócio recusada → mesmo corpo de erro do FastAPI ({"detail": ...})."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.on_event("shutdown")
def _flush_project_state_on_shutdown() -> None:
    """Fechar o app não pode perder a última gravação do annotations.coco.json."""
    from app.api import state as _state

    _state.coco_writer.flush(timeout=60)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "version": "2.0.0"}


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _base = Path(sys._MEIPASS)
else:
    _base = Path(__file__).resolve().parents[2]

FRONTEND_DIST = _base / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
