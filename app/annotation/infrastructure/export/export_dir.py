"""Guarda das pastas de exportacao: so apaga o que o proprio InoLabel criou.

Os exportadores YOLO recriam a pasta de destino do zero. Antes faziam isso com
shutil.rmtree em qualquer caminho recebido — um destino errado (a pasta do projeto,
~/Documentos, o dataset de origem) era apagado sem aviso. Agora toda pasta criada
por uma exportacao recebe um marcador, e so pastas marcadas (ou vazias) sao recriadas.
"""

from __future__ import annotations

import shutil
from pathlib import Path

EXPORT_MARKER = ".inolabel_export"


class UnsafeExportDirError(ValueError):
    """Destino de exportacao que o InoLabel se recusa a apagar ou usar."""


def is_inolabel_export(path: Path) -> bool:
    return (Path(path) / EXPORT_MARKER).is_file()


def mark_export_dir(path: Path) -> None:
    marker = Path(path) / EXPORT_MARKER
    if not marker.exists():
        marker.write_text("Pasta criada por uma exportacao do InoLabel.\n", encoding="utf-8")


def ensure_export_dir(path: Path) -> Path:
    """Cria (ou reaproveita) a pasta de exportacao sem apagar nada; marca como do InoLabel."""
    path = Path(path)
    if path.exists():
        if not path.is_dir():
            raise UnsafeExportDirError(f"O destino de exportacao nao e uma pasta: {path}")
        if any(path.iterdir()) and not is_inolabel_export(path):
            raise UnsafeExportDirError(
                f"A pasta {path} ja existe e nao foi criada pelo InoLabel; nada foi alterado."
            )
    path.mkdir(parents=True, exist_ok=True)
    mark_export_dir(path)
    return path


def reset_export_dir(path: Path) -> Path:
    """Esvazia e recria a pasta de exportacao — apenas se ela estiver vazia ou marcada."""
    path = Path(path)
    if path.exists():
        if not path.is_dir():
            raise UnsafeExportDirError(f"O destino de exportacao nao e uma pasta: {path}")
        if any(path.iterdir()):
            if not is_inolabel_export(path):
                raise UnsafeExportDirError(
                    f"A pasta {path} ja existe e nao foi criada pelo InoLabel; nada foi apagado."
                )
            shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    mark_export_dir(path)
    return path
