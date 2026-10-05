"""Leitura do arquivo de estado (annotations.coco.json) ao retomar uma sessao.

Um estado ilegivel nunca pode ser tratado como "sessao vazia": o primeiro autosave
gravaria por cima de um arquivo que talvez desse para recuperar. A leitura falha
alto, e a abertura da sessao e interrompida antes de qualquer gravacao.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class AnnotationStateUnreadableError(RuntimeError):
    def __init__(self, path: Path, cause: Exception):
        self.path = Path(path)
        self.cause = cause
        super().__init__(
            "Nao foi possivel ler o estado de anotacoes:\n"
            f"{self.path}\n\n"
            f"Motivo: {cause}\n\n"
            "A sessao nao foi aberta e o arquivo nao foi alterado. Restaure uma copia "
            "(ex.: o .bak ao lado dele) ou corrija o JSON antes de continuar."
        )


def read_annotation_state(path: Optional[Path]) -> Optional[dict]:
    """Conteudo do estado, None se ainda nao existe; AnnotationStateUnreadableError se ilegivel."""
    if path is None:
        return None
    path = Path(path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AnnotationStateUnreadableError(path, exc) from exc
    if not isinstance(data, dict):
        raise AnnotationStateUnreadableError(path, ValueError("o JSON nao e um objeto COCO"))
    return data
