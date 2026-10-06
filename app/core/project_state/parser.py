"""COCO do projeto → anotações em memória (índices de frame, categorias a partir de 0)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from app.core.project_state.paths import relative_name


def keypoint_specs_from_payload(data: dict, classes: Sequence[str]) -> List[dict]:
    """Pontos/esqueleto por classe lidos das categorias do COCO (para retomar projeto)."""
    by_name = {str(c.get("name", "")).strip(): c for c in data.get("categories", []) or []}
    specs = []
    for name in classes:
        cat = by_name.get(name) or {}
        specs.append({
            "keypoints": [str(k) for k in cat.get("keypoints", []) or []],
            "skeleton": [list(link) for link in cat.get("skeleton", []) or []],
        })
    return specs


@dataclass
class ParsedState:
    """Estado lido do COCO, já em índices de frame e categorias a partir de 0."""

    annotations: Dict[int, List[dict]] = field(default_factory=dict)
    dims: Dict[int, Tuple[int, int]] = field(default_factory=dict)
    reviewed: Set[int] = field(default_factory=set)
    image_ids: Dict[str, int] = field(default_factory=dict)
    max_annotation_id: int = 0
    unmatched_images: int = 0          # no COCO, mas sem imagem correspondente no dataset
    skipped_annotations: int = 0       # categoria inexistente ou bbox inválida


def parse_payload(
    data: dict,
    *,
    frame_paths: Sequence[Path],
    data_path: Optional[Path],
    num_classes: int,
) -> ParsedState:
    """Converte o COCO do projeto em anotações por índice de frame.

    Aceita ``file_name`` relativo ao dataset (formato atual) e só o nome do arquivo
    (projetos antigos), quando o nome é único no dataset.
    """
    parsed = ParsedState()
    by_relative = {relative_name(p, data_path): i for i, p in enumerate(frame_paths)}
    by_name: Dict[str, Optional[int]] = {}
    for i, p in enumerate(frame_paths):
        by_name[p.name] = None if p.name in by_name else i   # None = nome repetido

    index_by_image_id: Dict[object, int] = {}
    for img in data.get("images", []) or []:
        name = str(img.get("file_name", ""))
        idx = by_relative.get(name)
        if idx is None:
            idx = by_name.get(Path(name).name)
        if idx is None:
            parsed.unmatched_images += 1
            continue
        index_by_image_id[img.get("id")] = idx
        parsed.image_ids[relative_name(frame_paths[idx], data_path)] = int(img.get("id"))
        width, height = int(img.get("width", 0) or 0), int(img.get("height", 0) or 0)
        if width and height:
            parsed.dims[idx] = (width, height)
        parsed.reviewed.add(idx)

    category_ids = {cat.get("id"): pos for pos, cat in enumerate(data.get("categories", []) or [])}
    for ann in data.get("annotations", []) or []:
        idx = index_by_image_id.get(ann.get("image_id"))
        if idx is None:
            continue
        category = category_ids.get(ann.get("category_id"))
        bbox = ann.get("bbox")
        if category is None or category >= num_classes or not isinstance(bbox, list) or len(bbox) != 4:
            parsed.skipped_annotations += 1
            continue
        try:
            ann_id = int(ann.get("id"))
        except (TypeError, ValueError):
            parsed.skipped_annotations += 1
            continue
        entry = {
            "id": ann_id,
            "image_id": idx,
            "category_id": category,
            "bbox": [float(v) for v in bbox],
            "source": ann.get("source") or "manual",
            "score": ann.get("score"),
            "track_id": ann.get("track_id"),
            "obb": ann.get("obb"),
        }
        flat = ann.get("keypoints")
        if isinstance(flat, list) and flat:
            entry["keypoints"] = [
                [float(flat[i]), float(flat[i + 1]), int(flat[i + 2])] for i in range(0, len(flat) - 2, 3)
            ]
        parsed.annotations.setdefault(idx, []).append(entry)
        parsed.max_annotation_id = max(parsed.max_annotation_id, ann_id)

    # "revisado" = imagem presente no COCO sem anotações (negativo marcado);
    # imagens com anotações já entram pelo próprio annotation_store.
    parsed.reviewed -= set(parsed.annotations)
    return parsed
