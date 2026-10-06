"""Referencias anonimas para logs (LGPD).

Nomes de arquivo e de video de datasets de pessoas podem conter nomes ou
identificadores ("joao_silva_01.jpg"). Logs nao devem registra-los: usam uma
referencia curta e estavel (o mesmo arquivo gera sempre o mesmo codigo), suficiente
para correlacionar mensagens sem expor o nome. A interface pode continuar mostrando
o nome ao proprio usuario.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union


def log_ref(name: Union[str, Path, None]) -> str:
    """Ex.: '<arquivo 3f2a91c0>'. Nunca contem o nome original."""
    if name is None or str(name) == "":
        return "<arquivo ?>"
    digest = hashlib.sha1(str(name).encode("utf-8")).hexdigest()[:8]
    return f"<arquivo {digest}>"


def silence_opencv_path_logs() -> None:
    """Os avisos do OpenCV (ex.: imread que falha) incluem o caminho do arquivo."""
    try:
        import cv2  # pylint: disable=import-outside-toplevel

        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
    except Exception:  # pylint: disable=broad-except
        pass
