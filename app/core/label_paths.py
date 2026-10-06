"""Onde fica o .txt de anotações de cada imagem.

O label acompanha o caminho relativo da imagem dentro do dataset
(``labels/lote_a/img.txt``). Nomeá-lo só pelo stem fazia ``lote_a/img.jpg`` e
``lote_b/img.jpg`` gravarem no mesmo arquivo: uma anotação sobrescrevia a outra e
a exportação atribuía a caixa de uma imagem à outra.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable, Optional, Set

LABELS_DIR = "labels"


def legacy_label_path(output_path: Path, frame_path: Path) -> Path:
    """Formato antigo: ``labels/<stem>.txt``, sem a subpasta."""
    return Path(output_path) / LABELS_DIR / (Path(frame_path).stem + ".txt")


def label_path(output_path: Path, frame_path: Path, data_path: Optional[Path]) -> Path:
    """``labels/<caminho relativo ao dataset>.txt``.

    Imagem na raiz do dataset, dataset de arquivo único ou imagem fora do dataset
    caem em ``labels/<stem>.txt`` — o mesmo nome do formato antigo.
    """
    frame_path = Path(frame_path)
    if data_path is not None:
        try:
            relative = frame_path.relative_to(Path(data_path))
        except ValueError:
            relative = None
        if relative is not None and len(relative.parts) > 1:
            return Path(output_path) / LABELS_DIR / relative.with_suffix(".txt")
    return legacy_label_path(output_path, frame_path)


def ambiguous_stems(frame_paths: Iterable[Path]) -> Set[str]:
    """Stems que aparecem em mais de uma imagem do dataset."""
    counts = Counter(Path(p).stem for p in frame_paths)
    return {stem for stem, count in counts.items() if count > 1}


def find_label_file(
    output_path: Path,
    frame_path: Path,
    data_path: Optional[Path],
    ambiguous: Set[str],
) -> Optional[Path]:
    """Arquivo de label existente para a imagem, ou None.

    Prefere o caminho novo. O arquivo antigo (``labels/<stem>.txt``) só é aceito
    quando o stem é único no dataset: com nomes repetidos não há como saber de qual
    imagem ele era, e adivinhar colocaria caixas na imagem errada.
    """
    current = label_path(output_path, frame_path, data_path)
    if current.is_file():
        return current
    legacy = legacy_label_path(output_path, frame_path)
    if legacy != current and Path(frame_path).stem not in ambiguous and legacy.is_file():
        return legacy
    return None
