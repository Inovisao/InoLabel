"""``annotations.coco.json`` como estado do projeto (formato da versão 1.0.0).

O ``.txt`` YOLO de cada frame não guarda ``track_id``, ``source`` nem ``score``; o
COCO guarda tudo e é a base dos scripts de treino. Ele é a fonte da verdade do
projeto: carregado inteiro ao abrir, regravado a cada alteração.

Contrato (igual ao 1.0.0):
- ``categories[].id`` começa em 1 (a API usa índice a partir de 0 internamente);
- ``bbox`` em pixels ``[x, y, largura, altura]``, recortada à imagem;
- ``images[].file_name`` é o caminho relativo ao dataset, com ``/``;
- ``image.id`` e ``annotation.id`` são estáveis entre gravações;
- imagem revisada sem objetos entra em ``images`` sem anotações (negativo).

Funções puras: sem FastAPI e sem estado global, para serem testadas isoladamente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from app import __version__ as APP_VERSION
from app.annotation.core.export.yolo_label_service import clip_coco_bbox
from app.core.palette import CLASS_COLORS

STATE_SUBDIR = "saved_data_states"
_STATE_FILE_BY_MODE = {
    "obb": "annotations_obb.coco.json",
    "keypoint": "annotations_keypoints.coco.json",   # mesmo nome da 1.0.0
}
DEFAULT_STATE_FILE = "annotations.coco.json"


def state_path(output_path: Path, mode: str) -> Path:
    return Path(output_path) / STATE_SUBDIR / _STATE_FILE_BY_MODE.get(mode, DEFAULT_STATE_FILE)


def relative_name(frame_path: Path, data_path: Optional[Path]) -> str:
    """Caminho da imagem relativo ao dataset (``lote_a/img.jpg``), ou só o nome."""
    frame_path = Path(frame_path)
    if data_path is not None:
        try:
            return frame_path.relative_to(Path(data_path)).as_posix()
        except ValueError:
            pass
    return frame_path.name


def _field(ann, name, default=None):
    """Lê um campo de um Annotation (pydantic) ou de um dict."""
    if isinstance(ann, Mapping):
        return ann.get(name, default)
    return getattr(ann, name, default)


def build_payload(
    *,
    mode: str,
    classes: Sequence[str],
    data_path: Optional[Path],
    frame_paths: Sequence[Path],
    frame_dims: Mapping[int, Tuple[int, int]],
    annotation_store: Mapping[int, Iterable],
    reviewed: Iterable[int] = (),
    image_ids: Optional[Dict[str, int]] = None,
    current_index: Optional[int] = None,
    keypoint_specs: Sequence[Mapping] = (),
) -> dict:
    """Monta o COCO do projeto a partir do estado em memória.

    ``image_ids`` (``file_name → id``) é atualizado no lugar: imagens novas recebem
    o próximo id livre, e as já conhecidas mantêm o seu.
    Frames sem dimensões conhecidas são omitidos — quem chama garante as dimensões.
    """
    image_ids = image_ids if image_ids is not None else {}
    reviewed = set(reviewed)
    indices = sorted(
        idx for idx in set(annotation_store) | reviewed
        if 0 <= idx < len(frame_paths) and (annotation_store.get(idx) or idx in reviewed)
    )

    images: List[dict] = []
    annotations: List[dict] = []
    next_image_id = max(image_ids.values(), default=0) + 1
    for idx in indices:
        dims = frame_dims.get(idx)
        if not dims or not dims[0] or not dims[1]:
            continue
        width, height = int(dims[0]), int(dims[1])
        name = relative_name(frame_paths[idx], data_path)
        if name not in image_ids:
            image_ids[name] = next_image_id
            next_image_id += 1
        image_id = image_ids[name]
        images.append({"id": image_id, "file_name": name, "width": width, "height": height})

        for ann in annotation_store.get(idx) or []:
            category = int(_field(ann, "category_id", -1))
            if category < 0 or category >= len(classes):
                continue
            if mode == "keypoint":
                entry = _keypoint_entry(ann, image_id, category, width, height)
                if entry is not None:
                    annotations.append(entry)
                continue
            clipped = clip_coco_bbox(list(_field(ann, "bbox", [])), width, height)
            if clipped is None:
                continue
            x, y, w, h = clipped
            score = _field(ann, "score")
            entry = {
                "id": int(_field(ann, "id")),
                "image_id": image_id,
                "category_id": category + 1,
                "bbox": [x, y, w, h],
                "area": w * h,
                "iscrowd": 0,
                "segmentation": [],
                "score": float(score) if score is not None else 1.0,
                "source": _field(ann, "source", "manual") or "manual",
            }
            track_id = _field(ann, "track_id")
            if mode == "tracking" and track_id is not None:
                entry["track_id"] = int(track_id)
            obb = _field(ann, "obb")
            if obb is not None:
                entry["obb"] = obb if isinstance(obb, Mapping) else obb.model_dump(exclude_none=True)
            annotations.append(entry)

    payload = {
        "info": {
            "description": "InoLabel — estado do projeto",
            "version": "1.0",
            "app_version": APP_VERSION,
            "task_mode": mode,
            "data_root": str(data_path) if data_path is not None else "",
        },
        "licenses": [],
        "categories": [_category(i, name, mode, keypoint_specs) for i, name in enumerate(classes)],
        "images": images,
        "annotations": annotations,
    }
    if current_index is not None and 0 <= current_index < len(frame_paths):
        payload["annotation_state"] = {
            "last_active_file_name": relative_name(frame_paths[current_index], data_path),
            "last_active_frame_index": int(current_index),
        }
    return payload


def _category(index: int, name: str, mode: str, keypoint_specs: Sequence[Mapping]) -> dict:
    category = {"id": index + 1, "name": name, "color": CLASS_COLORS[index % len(CLASS_COLORS)], "supercategory": "none"}
    if mode == "keypoint":
        spec = keypoint_specs[index] if index < len(keypoint_specs) else {}
        category["keypoints"] = list(spec.get("keypoints", []))
        category["skeleton"] = [list(link) for link in spec.get("skeleton", [])]
    return category


def _keypoint_entry(ann, image_id: int, category: int, width: int, height: int) -> Optional[dict]:
    """Anotação no padrão COCO Keypoints; pontos presos à imagem, bbox = envelope dos visíveis."""
    points = _field(ann, "keypoints") or []
    flat: List[float] = []
    placed = []
    for kp in points:
        x, y, v = float(kp[0]), float(kp[1]), int(kp[2])
        if v > 0:
            x, y = min(max(x, 0.0), float(width)), min(max(y, 0.0), float(height))
            placed.append((x, y))
        else:
            x = y = 0.0
        flat.extend([x, y, v])
    if not placed:
        return None   # instância sem nenhum ponto marcado não é válida
    xs = [p[0] for p in placed]
    ys = [p[1] for p in placed]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    score = _field(ann, "score")
    return {
        "id": int(_field(ann, "id")),
        "image_id": image_id,
        "category_id": category + 1,
        "bbox": [x0, y0, w, h],
        "area": w * h,
        "iscrowd": 0,
        "segmentation": [],
        "keypoints": flat,
        "num_keypoints": len(placed),
        "score": float(score) if score is not None else 1.0,
        "source": _field(ann, "source", "manual") or "manual",
    }


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
