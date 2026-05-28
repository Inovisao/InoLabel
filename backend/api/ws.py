"""WebSocket para streaming de frames e eventos em tempo real."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.session_manager import session_manager

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)

# Conjunto de conexoes ativas
_connections: Set[WebSocket] = set()


async def _broadcast(data: dict) -> None:
    """Envia estado para todos os clientes conectados."""
    if not _connections:
        return
    payload = json.dumps(data)
    dead: Set[WebSocket] = set()
    for ws in list(_connections):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


def _sync_broadcast(data: dict) -> None:
    """Callback síncrono chamado pelo SessionManager (thread do tool)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast(data))
        else:
            loop.run_until_complete(_broadcast(data))
    except RuntimeError:
        pass


# Registra o callback global de broadcast
session_manager.add_frame_listener(_sync_broadcast)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _connections.add(ws)
    logger.info("WebSocket conectado. Total: %d", len(_connections))

    # Envia estado atual imediatamente ao conectar
    try:
        state = session_manager.get_state()
        await ws.send_text(json.dumps(state))
    except Exception:
        pass

    try:
        while True:
            raw = await ws.receive_text()
            await _handle_client_message(ws, raw)
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(ws)
        logger.info("WebSocket desconectado. Total: %d", len(_connections))


async def _handle_client_message(ws: WebSocket, raw: str) -> None:
    """Processa mensagens enviadas pelo frontend via WebSocket."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return

    action = msg.get("action")
    tool = session_manager.tool
    if tool is None:
        return

    try:
        if action == "accept":
            tool.on_accept()
        elif action == "reject":
            tool.on_reject()
        elif action == "undo":
            if hasattr(tool, "undo_last_action"):
                tool.undo_last_action()
        elif action == "toggle_annotation":
            if hasattr(tool, "toggle_annotation_mode"):
                tool.toggle_annotation_mode()
        elif action == "toggle_remove":
            if hasattr(tool, "toggle_remove_mode"):
                tool.toggle_remove_mode()
        elif action == "toggle_pan":
            if hasattr(tool, "toggle_pan_mode"):
                tool.toggle_pan_mode()
        elif action == "toggle_selection":
            if hasattr(tool, "toggle_selection_mode"):
                tool.toggle_selection_mode()
        elif action == "reset_zoom":
            if hasattr(tool, "reset_zoom"):
                tool.reset_zoom()
        elif action == "ping":
            await ws.send_text(json.dumps({"event": "pong"}))
            return
        else:
            return
    except Exception as exc:
        logger.warning("Erro ao processar acao '%s': %s", action, exc)
        return

    state = session_manager.get_state()
    await _broadcast(state)
