"""FastAPI application for the InoLabel WebUI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import annotations, classes, export, frames, keybinds, modes, session, validation

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

app.include_router(modes.router)
app.include_router(validation.router)
app.include_router(session.router)
app.include_router(export.router)
app.include_router(keybinds.router)
app.include_router(frames.router)
app.include_router(annotations.router)
app.include_router(classes.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "version": "2.0.0"}


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
