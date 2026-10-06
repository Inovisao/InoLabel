"""Arquivos .txt espelho (formato YOLO do modo) em labels/: escrita e leitura.

O estado do projeto é o annotations.coco.json; o .txt é espelho e fonte de migração."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from app.annotation_keypoint.infrastructure.export.yolo_pose_exporter import format_pose_line
from app.api import state as _state
from app.api.annotations.obb import obb_from_points, points_from_obb
from app.api.common.schemas import Annotation
from app.core.label_paths import find_label_file, label_path, legacy_label_path

log = logging.getLogger(__name__)


# Tracks which labels/ directories have already been created this session,
# avoiding a redundant mkdir syscall on every autosave.

_labels_dir_created: set[str] = set()


def reset_label_dir_cache() -> None:
    _labels_dir_created.clear()


def label_lines(session, annotations: List[Annotation], img_w: int, img_h: int) -> List[str]:
    """Linhas do .txt espelho no formato YOLO do modo (caixa, OBB ou pose)."""
    lines: List[str] = []
    n_kpts = max((len(spec.get("keypoints", [])) for spec in session.keypoint_specs or []), default=0)
    for ann in annotations:
        if session.mode == "keypoint":
            if ann.keypoints:
                lines.append(format_pose_line(ann.category_id, ann.keypoints, img_w, img_h, n_kpts))
            continue
        if session.mode == "obb" and ann.obb is not None:
            points = ann.obb.points or points_from_obb(ann.obb)
            values = [str(ann.category_id)]
            for px, py in points:
                values.append(f"{max(0.0, min(1.0, float(px) / img_w)):.6f}")
                values.append(f"{max(0.0, min(1.0, float(py) / img_h)):.6f}")
            lines.append(" ".join(values))
            continue

        x, y, w, h = ann.bbox
        x = max(0.0, x)
        y = max(0.0, y)
        w = min(w, img_w - x)
        h = min(h, img_h - y)
        if w <= 0 or h <= 0:
            continue
        cx = (x + w / 2) / img_w
        cy = (y + h / 2) / img_h
        wn = w / img_w
        hn = h / img_h
        lines.append(f"{ann.category_id} {cx:.6f} {cy:.6f} {wn:.6f} {hn:.6f}")

    return lines


def write_label_file(session, image_id: int, img_w: int, img_h: int) -> Path:
    """Regrava o .txt espelho do frame (labels/<caminho relativo da imagem>.txt)."""
    path = _state.frame_paths[image_id]
    annotations: List[Annotation] = _state.annotation_store.get(image_id, [])

    # O label acompanha a subpasta da imagem: nomeá-lo só pelo stem fazia imagens
    # de mesmo nome em pastas diferentes sobrescreverem o label uma da outra.
    txt_path = label_path(session.output_path, path, session.data_path)
    labels_key = str(txt_path.parent)
    if labels_key not in _labels_dir_created:
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        _labels_dir_created.add(labels_key)

    lines = label_lines(session, annotations, img_w, img_h)
    txt_path.write_text("\n".join(lines) + ("\n" if lines else ""))
    log.debug("autosave: %d annotations → %s", len(lines), txt_path)

    # Projeto gravado no formato antigo (labels/<stem>.txt): o conteúdo acabou de
    # ser regravado no lugar novo, então a cópia velha sai para não divergir. Só
    # quando o stem é único — com nomes repetidos o arquivo antigo pode ser de
    # outra imagem.
    legacy = legacy_label_path(session.output_path, path)
    if legacy != txt_path and path.stem not in _state.ambiguous_frame_stems():
        legacy.unlink(missing_ok=True)
    return txt_path


def load_labels_from_txt(
    image_id: int, path: Path, img_w: int, img_h: int, output_path: Path
) -> None:
    """Load YOLO annotations from disk into annotation_store for a single frame."""
    session = _state.active_session()
    txt_path = find_label_file(
        output_path, path, session.data_path if session is not None else None,
        _state.ambiguous_frame_stems(),
    )
    if txt_path is None:
        return

    anns: List[Annotation] = []
    try:
        for line in txt_path.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            cls_id = int(parts[0])
            obb = None
            if len(parts) >= 9:
                points = [
                    [float(parts[i]) * img_w, float(parts[i + 1]) * img_h]
                    for i in range(1, 9, 2)
                ]
                obb = obb_from_points(points)
                x = min(point[0] for point in points)
                y = min(point[1] for point in points)
                w = max(point[0] for point in points) - x
                h = max(point[1] for point in points) - y
            else:
                cx, cy, wn, hn = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                w = wn * img_w
                h = hn * img_h
                x = cx * img_w - w / 2
                y = cy * img_h - h / 2
            anns.append(Annotation(
                id=_state.next_ann_id[0],
                image_id=image_id,
                category_id=cls_id,
                bbox=[x, y, w, h],
                obb=obb,
                source="file",
            ))
            _state.next_ann_id[0] += 1
    except Exception:
        log.exception("Failed to load %s", txt_path)
        return

    if anns:
        _state.annotation_store[image_id] = anns
        log.debug("loaded %d annotations from %s", len(anns), txt_path)
