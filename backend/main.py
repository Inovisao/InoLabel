"""Entry point do servidor FastAPI — serve a API e o frontend React (dist/)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.session import router as session_router
from backend.api.frame import router as frame_router
from backend.api.export import router as export_router
from backend.api.wizard import router as wizard_router
from backend.api.ws import router as ws_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

app = FastAPI(title="InoLabel API", version="2.0.0")

# CORS para desenvolvimento (React dev server na porta 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(session_router)
app.include_router(frame_router)
app.include_router(export_router)
app.include_router(wizard_router)
app.include_router(ws_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# ── Serve frontend React (build de producao) ─────────────────────────────────
def _find_dist() -> Path | None:
    """Localiza frontend/dist tanto em dev quanto no bundle PyInstaller."""
    # Bundle: assets estao em sys._MEIPASS
    if getattr(sys, "frozen", False):
        candidate = Path(sys._MEIPASS) / "frontend" / "dist"  # type: ignore[attr-defined]
        if candidate.exists():
            return candidate
        return None
    # Dev: dois niveis acima deste arquivo (backend/main.py → raiz)
    candidate = Path(__file__).parent.parent / "frontend" / "dist"
    return candidate if candidate.exists() else None


_dist = _find_dist()
if _dist:
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
