"""Gerencia a instancia ativa da ferramenta de anotacao."""

from __future__ import annotations

import asyncio
import base64
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from backend.core.session import AnnotationSessionConfig, AnnotationTaskMode


class SessionManager:
    """Singleton que mantém a ferramenta ativa e notifica listeners via callback."""

    def __init__(self) -> None:
        self._tool: Any = None
        self._lock = threading.Lock()
        self._frame_listeners: list[Callable[[bytes, dict], None]] = []

    # ── Ciclo de vida da sessão ───────────────────────────────────────────────

    def start(self, config: AnnotationSessionConfig) -> None:
        with self._lock:
            if self._tool is not None:
                try:
                    self._tool.finish_processing("Nova sessao iniciada.")
                except Exception:
                    pass
            self._tool = self._build_tool(config)

    def stop(self) -> None:
        with self._lock:
            if self._tool is not None:
                try:
                    self._tool.finish_processing("Sessao encerrada.")
                except Exception:
                    pass
                self._tool = None

    @property
    def tool(self) -> Any:
        return self._tool

    @property
    def active(self) -> bool:
        return self._tool is not None

    # ── Frame ────────────────────────────────────────────────────────────────

    def get_frame_b64(self) -> str:
        """Retorna frame atual renderizado como base64 JPEG."""
        if self._tool is None:
            return ""
        raw = self._tool.render_frame()
        return base64.b64encode(raw).decode() if raw else ""

    def get_state(self) -> dict:
        if self._tool is None:
            return {"active": False}
        snap = self._tool.get_state_snapshot()
        snap["active"] = True
        snap["frame_b64"] = self.get_frame_b64()
        return snap

    # ── Listeners (WebSocket broadcast) ─────────────────────────────────────

    def add_frame_listener(self, cb: Callable[[dict], None]) -> None:
        self._frame_listeners.append(cb)

    def remove_frame_listener(self, cb: Callable[[dict], None]) -> None:
        self._frame_listeners = [l for l in self._frame_listeners if l is not cb]

    def notify_frame_update(self) -> None:
        """Chama todos os listeners com o estado atual. Thread-safe."""
        state = self.get_state()
        for cb in list(self._frame_listeners):
            try:
                cb(state)
            except Exception:
                pass

    # ── Construção da ferramenta ─────────────────────────────────────────────

    @staticmethod
    def _build_tool(config: AnnotationSessionConfig):
        if config.mode is AnnotationTaskMode.OBB:
            from backend.annotation_obb.tool import OBBAnnotationTool
            return OBBAnnotationTool(session_config=config)
        if config.mode is AnnotationTaskMode.CLASSIFICATION:
            from backend.services.classification_service import ClassificationService
            return ClassificationService(session_config=config)
        from backend.annotation.tool import AnnotationTool
        return AnnotationTool(session_config=config)


# Instância global (uma por processo)
session_manager = SessionManager()
