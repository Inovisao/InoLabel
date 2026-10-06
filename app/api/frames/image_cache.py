"""Imagens dos frames codificadas em JPEG/base64, com cache LRU e pré-carregamento.

Guarda as últimas N imagens decodificadas para que voltar e avançar não releia o disco,
e decodifica os vizinhos em segundo plano. Ler a imagem também registra as dimensões
do frame em ``state.frame_dims``.
"""

from __future__ import annotations

import base64
import threading
from collections import OrderedDict
from typing import Optional

import cv2

from app.api import state as _state

_CACHE_MAX = 8
_JPEG_QUALITY = 85

_cache: OrderedDict[int, str] = OrderedDict()
# Índices sendo decodificados agora numa thread de fundo.
_prefetching: set[int] = set()


def clear() -> None:
    _cache.clear()
    _prefetching.clear()


def cached(index: int) -> Optional[str]:
    """Imagem já codificada (marcada como usada recentemente), ou None."""
    if index not in _cache:
        return None
    _cache.move_to_end(index)
    return _cache[index]


def encode(index: int) -> Optional[str]:
    """Lê, registra as dimensões e codifica o frame; None se a imagem não abre."""
    img = cv2.imread(str(_state.frame_paths[index]))
    if img is None:
        return None
    h, w = img.shape[:2]
    _state.frame_dims[index] = (w, h)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
    b64 = base64.b64encode(buf).decode()
    _store(index, b64)
    return b64


def prefetch(index: int) -> None:
    """Decodifica o frame numa thread de fundo, se ainda não está no cache nem a caminho."""
    if not _valid(index) or index in _cache or index in _prefetching:
        return
    _prefetching.add(index)
    threading.Thread(target=_prefetch_worker, args=(index,), daemon=True).start()


def _prefetch_worker(index: int) -> None:
    # Falhas aqui são ignoradas: o frame é lido de novo quando for exibido.
    try:
        if _valid(index) and index not in _cache:
            encode(index)
    except Exception:
        pass
    finally:
        _prefetching.discard(index)


def _store(index: int, b64: str) -> None:
    if index not in _cache:
        _cache[index] = b64
        if len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


def _valid(index: int) -> bool:
    return 0 <= index < len(_state.frame_paths)
