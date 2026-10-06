from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from app.api import state as _state
from app.annotation.infrastructure.persistence.state_file import read_annotation_state
from app.core.coco_state import build_payload, parse_payload, state_path
from app.core.label_paths import find_label_file, label_path, legacy_label_path
from app.api.schemas import (
    Annotation,
    AnnotationUpsert,
    ClassificationResult,
    ClassificationUpsert,
    AnnotationPatch,
    ClassificationState as ClassificationStateResponse,
    FrameReviewState,
    NextTrackId,
    OBBGeometry,
    ReviewedUpdate,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/annotations", tags=["annotations"])

# All annotation data lives in _state.annotation_store (shared with frames.py)
# _state.next_ann_id[0] is the next annotation id counter

# Tracks which labels/ directories have already been created this session,
# avoiding a redundant mkdir syscall on every autosave.
_labels_dir_created: set[str] = set()


def reset_annotations() -> None:
    _state.annotation_store.clear()
    _state.next_ann_id[0] = 1
    _state.reviewed_frames.clear()
    _state.coco_image_ids.clear()
    _labels_dir_created.clear()


def _frame_dims(image_id: int):
    """(largura, altura) do frame; lê só o cabeçalho da imagem se ainda não conhecido."""
    dims = _state.frame_dims.get(image_id)
    if dims is not None:
        return dims
    if image_id < 0 or image_id >= len(_state.frame_paths):
        return None
    try:
        from PIL import Image as _PIL

        with _PIL.open(_state.frame_paths[image_id]) as im:
            dims = im.size
    except Exception:
        return None
    _state.frame_dims[image_id] = dims
    return dims


def save_project_state() -> None:
    """Regrava o annotations.coco.json do projeto (em segundo plano)."""
    session = _state.active_session()
    if session is None or session.mode == "classification":
        return
    for idx in set(_state.annotation_store) | _state.reviewed_frames:
        _frame_dims(idx)
    payload = build_payload(
        mode=session.mode,
        classes=session.classes,
        data_path=session.data_path,
        frame_paths=_state.frame_paths,
        frame_dims=_state.frame_dims,
        annotation_store=_state.annotation_store,
        reviewed=_state.reviewed_frames,
        image_ids=_state.coco_image_ids,
        current_index=session.current_frame,
    )
    _state.coco_writer.submit(state_path(session.output_path, session.mode), payload)


def bootstrap_project_state() -> set:
    """Carrega o projeto inteiro ao abrir; devolve os frames que já estão em memória.

    O COCO é a fonte da verdade. Sem ele (projeto anterior a esta versão), as
    anotações vêm dos .txt e o COCO é gerado na hora, migrando o projeto.
    """
    session = _state.active_session()
    if session is None or session.mode == "classification" or not _state.frame_paths:
        return set()
    data = read_annotation_state(state_path(session.output_path, session.mode))
    if data is not None:
        parsed = parse_payload(
            data, frame_paths=_state.frame_paths, data_path=session.data_path,
            num_classes=len(session.classes),
        )
        for idx, entries in parsed.annotations.items():
            _state.annotation_store[idx] = [_annotation_from_state(e) for e in entries]
        _state.frame_dims.update(parsed.dims)
        _state.reviewed_frames.update(parsed.reviewed)
        _state.coco_image_ids.update(parsed.image_ids)
        _state.next_ann_id[0] = max(_state.next_ann_id[0], parsed.max_annotation_id + 1)
        if parsed.unmatched_images or parsed.skipped_annotations:
            log.warning(
                "estado do projeto: %d imagem(ns) sem correspondente no dataset, %d anotação(ões) ignorada(s)",
                parsed.unmatched_images, parsed.skipped_annotations,
            )
        return set(range(len(_state.frame_paths)))

    # Migração: lê os .txt existentes e grava o COCO pela primeira vez.
    ambiguous = _state.ambiguous_frame_stems()
    migrated = False
    for idx, frame_path in enumerate(_state.frame_paths):
        if find_label_file(session.output_path, frame_path, session.data_path, ambiguous) is None:
            continue
        dims = _frame_dims(idx)
        if dims is None:
            continue
        _load_frame_from_txt(idx, frame_path, dims[0], dims[1], session.output_path)
        migrated = migrated or bool(_state.annotation_store.get(idx))
    if migrated:
        save_project_state()
    return set(range(len(_state.frame_paths)))


def _annotation_from_state(entry: dict) -> Annotation:
    obb = entry.get("obb")
    return Annotation(
        id=entry["id"],
        image_id=entry["image_id"],
        category_id=entry["category_id"],
        bbox=entry["bbox"],
        obb=OBBGeometry(**obb) if isinstance(obb, dict) else None,
        track_id=entry.get("track_id"),
        source=entry.get("source") or "manual",
        score=entry.get("score"),
    )


def _points_from_obb(obb: OBBGeometry) -> list[list[float]]:
    theta = math.radians(float(obb.angle))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    half_w = float(obb.width) / 2.0
    half_h = float(obb.height) / 2.0
    local = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)]
    return [
        [float(obb.cx + dx * cos_t - dy * sin_t), float(obb.cy + dx * sin_t + dy * cos_t)]
        for dx, dy in local
    ]


def _obb_from_bbox(bbox: list[float]) -> OBBGeometry:
    x, y, w, h = (float(value) for value in bbox)
    obb = OBBGeometry(
        cx=x + w / 2.0,
        cy=y + h / 2.0,
        width=w,
        height=h,
        angle=0.0,
        angle_unit="degrees",
    )
    obb.points = _points_from_obb(obb)
    return obb


def _obb_from_points(points: list[list[float]]) -> OBBGeometry:
    p0, p1, p2, p3 = points
    cx = sum(point[0] for point in points) / 4.0
    cy = sum(point[1] for point in points) / 4.0
    width = math.dist(p0, p1)
    height = math.dist(p1, p2)
    angle = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    return OBBGeometry(
        cx=cx,
        cy=cy,
        width=width,
        height=height,
        angle=angle,
        angle_unit="degrees",
        points=points,
    )


def _autosave(image_id: int) -> None:
    """Write YOLO txt for this frame. Failures are logged and never surface as HTTP errors."""
    try:
        import cv2 as _cv2

        session = _state.active_session()
        if session is None:
            return
        if not _state.frame_paths or image_id >= len(_state.frame_paths):
            return
        dims = _state.frame_dims.get(image_id)
        if dims is None:
            # Frame not yet loaded through the UI — read dims from disk so we never
            # silently discard annotations added before the frame is displayed.
            img_path = _state.frame_paths[image_id]
            img = _cv2.imread(str(img_path))
            if img is None:
                log.warning("autosave: cannot read image %s for frame %d — skipped", img_path.name, image_id)
                return
            h, w = img.shape[:2]
            dims = (w, h)
            _state.frame_dims[image_id] = dims

        img_w, img_h = dims
        if img_w == 0 or img_h == 0:
            return

        path = _state.frame_paths[image_id]
        annotations: List[Annotation] = _state.annotation_store.get(image_id, [])

        # O label acompanha a subpasta da imagem: nomeá-lo só pelo stem fazia imagens
        # de mesmo nome em pastas diferentes sobrescreverem o label uma da outra.
        txt_path = label_path(session.output_path, path, session.data_path)
        labels_key = str(txt_path.parent)
        if labels_key not in _labels_dir_created:
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            _labels_dir_created.add(labels_key)

        lines: List[str] = []
        for ann in annotations:
            if session.mode == "obb" and ann.obb is not None:
                points = ann.obb.points or _points_from_obb(ann.obb)
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

        txt_path.write_text("\n".join(lines) + ("\n" if lines else ""))
        log.debug("autosave: %d annotations → %s", len(lines), txt_path)
        save_project_state()

        # Projeto gravado no formato antigo (labels/<stem>.txt): o conteúdo acabou de
        # ser regravado no lugar novo, então a cópia velha sai para não divergir. Só
        # quando o stem é único — com nomes repetidos o arquivo antigo pode ser de
        # outra imagem.
        legacy = legacy_label_path(session.output_path, path)
        if legacy != txt_path and path.stem not in _state.ambiguous_frame_stems():
            legacy.unlink(missing_ok=True)

    except Exception:
        log.exception("autosave failed for frame %d", image_id)


def _load_frame_from_txt(
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
                obb = _obb_from_points(points)
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


def _ensure_loaded_from_disk(image_id: int) -> None:
    """Carrega do disco as anotações do frame antes da primeira mutação.

    Sem isso, anotar um frame ainda não exibido (API direta, inferência em lote)
    regravava o label só com a anotação nova e apagava as que já estavam salvas.
    """
    from app.api.routes import frames as _frames

    if image_id in _frames._loaded_from_disk or image_id in _state.annotation_store:
        return
    if image_id < 0 or image_id >= len(_state.frame_paths):
        return
    path = _state.frame_paths[image_id]
    dims = _state.frame_dims.get(image_id)
    if dims is None:
        try:
            from PIL import Image as _PIL

            with _PIL.open(path) as im:
                dims = im.size  # (width, height)
        except Exception:
            return
        _state.frame_dims[image_id] = dims
    _frames._lazy_load_from_disk(image_id, path, dims[0], dims[1])


@router.get("/debug")
def debug_store() -> dict:
    """Development helper — returns raw annotation_store contents."""
    return {
        "total_frames_with_annotations": len(_state.annotation_store),
        "frame_indices": list(_state.annotation_store.keys()),
        "counts": {k: len(v) for k, v in _state.annotation_store.items()},
        "next_id": _state.next_ann_id[0],
    }


@router.get("/next-track-id", response_model=NextTrackId)
def next_track_id() -> NextTrackId:
    """Próximo ID livre no projeto (maior track_id usado + 1)."""
    used = [
        int(ann.track_id)
        for anns in _state.annotation_store.values() for ann in anns
        if getattr(ann, "track_id", None) is not None
    ]
    return NextTrackId(next_track_id=max(used, default=0) + 1)


@router.get("/{image_id}", response_model=List[Annotation])
def get_annotations(image_id: int) -> List[Annotation]:
    return _state.annotation_store.get(image_id, [])


@router.post("/{image_id}", response_model=Annotation)
def add_annotation(image_id: int, body: AnnotationUpsert) -> Annotation:
    # Use frame_paths when available (fully loaded session); fall back to
    # session.total_frames so the guard works before any frame is fetched.
    session = _state.active_session()
    total = len(_state.frame_paths) or (session.total_frames if session else 0)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessao ativa nao encontrada.")
    if session.mode == "classification":
        raise HTTPException(
            status_code=422,
            detail="Classificacao nao usa bounding boxes; use /annotations/{image_id}/classification.",
        )
    if session.mode == "detection" and body.track_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Modo deteccao padrao nao aceita track_id.",
        )
    if session.mode == "tracking" and body.source == "model" and body.track_id is None:
        raise HTTPException(
            status_code=422,
            detail="Modo rastreamento exige track_id para anotacoes geradas pelo modelo.",
        )
    if total and image_id >= total:
        raise HTTPException(
            status_code=400,
            detail=f"image_id {image_id} fora do intervalo (sessão tem {total} frames, índices 0–{total - 1}).",
        )
    obb = body.obb
    if session.mode == "obb":
        obb = body.obb or _obb_from_bbox(body.bbox)
        if obb.points is None:
            obb.points = _points_from_obb(obb)

    _ensure_loaded_from_disk(image_id)
    ann = Annotation(
        id=_state.next_ann_id[0],
        image_id=image_id,
        category_id=body.category_id,
        bbox=body.bbox,
        obb=obb,
        track_id=body.track_id,
        source=body.source,
        score=body.score,
    )
    _state.annotation_store.setdefault(image_id, []).append(ann)
    _state.next_ann_id[0] += 1
    _autosave(image_id)
    return ann


def _classification_context(session):
    """(arquivo de estado, registros, pastas por classe) da sessão de classificação."""
    from app.classification.dataset import STATE_FILE_NAME, add_class_directory, load_state, prepare_dataset

    state_file = session.output_path / STATE_FILE_NAME
    records: list = []
    class_directories = prepare_dataset(session.output_path, session.classes)
    if state_file.exists():
        try:
            loaded = load_state(state_file)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if loaded is not None:
            records = list(loaded.records)
            class_directories.update(loaded.class_directories)
    for name in session.classes:
        if name not in class_directories:
            add_class_directory(session.output_path, name, class_directories)
    return state_file, records, class_directories


def _record_index(records: list, image_path: Path):
    """Posição do último registro desta imagem (a classificação vigente), ou None."""
    target = Path(image_path).resolve()
    for pos in range(len(records) - 1, -1, -1):
        if Path(records[pos].source_path).resolve() == target:
            return pos
    return None


def _write_classification(session, state_file, records, class_directories) -> None:
    from app.classification.dataset import write_state

    write_state(
        state_file,
        classes=session.classes,
        class_directories=class_directories,
        source_root=session.data_path,
        records=records,
    )
    session.saved_frames = len(records)
    session.annotation_count = len(records)


def _require_classification_frame(image_id: int):
    session = _state.active_session()
    if session is None:
        raise HTTPException(status_code=404, detail="Sessao ativa nao encontrada.")
    if session.mode != "classification":
        raise HTTPException(status_code=422, detail="Endpoint disponivel apenas no modo classificacao.")
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="No frames loaded. Call /frames/init first.")
    if image_id < 0 or image_id >= len(_state.frame_paths):
        raise HTTPException(status_code=400, detail="Index out of range.")
    return session


_classification_cache: dict = {"key": None, "by_source": {}}


def current_classification_id(image_path: Path):
    """Índice da classe já atribuída à imagem, lido do estado (cacheado pelo mtime)."""
    session = _state.active_session()
    if session is None or session.mode != "classification":
        return None
    from app.classification.dataset import STATE_FILE_NAME, load_state

    state_file = session.output_path / STATE_FILE_NAME
    try:
        key = (str(state_file), state_file.stat().st_mtime_ns)
    except OSError:
        return None
    if _classification_cache["key"] != key:
        by_source: dict = {}
        try:
            loaded = load_state(state_file)
        except ValueError:
            loaded = None
        for record in (loaded.records if loaded is not None else ()):
            by_source[str(Path(record.source_path).resolve())] = record.class_name
        _classification_cache.update(key=key, by_source=by_source)
    name = _classification_cache["by_source"].get(str(Path(image_path).resolve()))
    return session.classes.index(name) if name in session.classes else None


@router.post("/{image_id}/classification", response_model=ClassificationResult)
def classify_frame(image_id: int, body: ClassificationUpsert) -> ClassificationResult:
    """Classifica a imagem. Se ela já tinha classe, troca de pasta em vez de duplicar."""
    from app.classification.dataset import reclassify_record, transfer_image_to_class

    session = _require_classification_frame(image_id)
    if body.category_id >= len(session.classes):
        raise HTTPException(status_code=422, detail="category_id fora do intervalo de classes.")
    class_name = session.classes[body.category_id]
    state_file, records, class_directories = _classification_context(session)
    image_path = _state.frame_paths[image_id]

    pos = _record_index(records, image_path)
    if pos is not None:
        record = reclassify_record(
            records[pos], class_name=class_name,
            output_dir=session.output_path, class_directories=class_directories,
        )
        records[pos] = record
    else:
        record = transfer_image_to_class(
            image_path, class_name=class_name, output_dir=session.output_path,
            class_directories=class_directories, move=body.move_file,
        )
        records.append(record)
    _write_classification(session, state_file, records, class_directories)

    return ClassificationResult(
        image_id=image_id,
        filename=image_path.name,
        top1_class_id=body.category_id,
        top1_class_name=class_name,
        destination_path=str(record.destination_path),
        operation=record.operation,
    )


@router.get("/{image_id}/classification", response_model=ClassificationStateResponse)
def get_classification(image_id: int) -> ClassificationStateResponse:
    session = _require_classification_frame(image_id)
    class_id = current_classification_id(_state.frame_paths[image_id])
    return ClassificationStateResponse(
        image_id=image_id, class_id=class_id,
        class_name=session.classes[class_id] if class_id is not None else None,
    )


@router.delete("/{image_id}/classification", response_model=ClassificationStateResponse)
def undo_classification(image_id: int) -> ClassificationStateResponse:
    """Desfaz a classificação: apaga a cópia (ou devolve a imagem movida) e o registro."""
    from app.classification.dataset import undo_record

    session = _require_classification_frame(image_id)
    state_file, records, class_directories = _classification_context(session)
    pos = _record_index(records, _state.frame_paths[image_id])
    if pos is None:
        raise HTTPException(status_code=404, detail="Imagem ainda nao classificada.")
    undo_record(records.pop(pos))
    _write_classification(session, state_file, records, class_directories)
    return ClassificationStateResponse(image_id=image_id)


@router.post("/{image_id}/reviewed", response_model=FrameReviewState)
def set_reviewed(image_id: int, body: ReviewedUpdate) -> FrameReviewState:
    """Marca (ou desmarca) a imagem como revisada sem objetos: vira negativo no dataset."""
    session = _state.active_session()
    if session is None:
        raise HTTPException(status_code=404, detail="Sessao ativa nao encontrada.")
    if session.mode == "classification":
        raise HTTPException(status_code=422, detail="Classificacao nao usa revisao de negativos.")
    if image_id < 0 or image_id >= len(_state.frame_paths):
        raise HTTPException(status_code=400, detail="Index out of range.")
    if _frame_dims(image_id) is None:
        raise HTTPException(status_code=404, detail="Imagem ilegivel.")
    if body.reviewed:
        _state.reviewed_frames.add(image_id)
    else:
        _state.reviewed_frames.discard(image_id)
    save_project_state()
    return FrameReviewState(
        image_id=image_id,
        reviewed=image_id in _state.reviewed_frames,
        annotation_count=len(_state.annotation_store.get(image_id, [])),
    )


@router.patch("/{image_id}/{ann_id}", response_model=Annotation)
def update_annotation(image_id: int, ann_id: int, body: AnnotationPatch) -> Annotation:
    """Altera classe, ID de rastreamento ou geometria de uma anotação existente."""
    session = _state.active_session()
    if session is None:
        raise HTTPException(status_code=404, detail="Sessao ativa nao encontrada.")
    anns = _state.annotation_store.get(image_id, [])
    pos = next((i for i, a in enumerate(anns) if a.id == ann_id), None)
    if pos is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    changes = body.model_dump(exclude_unset=True)
    if "category_id" in changes and not 0 <= int(changes["category_id"]) < len(session.classes):
        raise HTTPException(status_code=422, detail="category_id fora do intervalo de classes.")
    if changes.get("track_id") is not None and session.mode != "tracking":
        raise HTTPException(status_code=422, detail="track_id so existe no modo rastreamento.")
    if "track_id" in changes and changes["track_id"] is not None and changes["track_id"] < 0:
        raise HTTPException(status_code=422, detail="track_id deve ser >= 0.")
    if "bbox" in changes:
        bbox = changes["bbox"]
        if bbox is None or len(bbox) != 4 or bbox[2] <= 0 or bbox[3] <= 0:
            raise HTTPException(status_code=422, detail="bbox deve ser [x, y, largura, altura] com area.")
    current = anns[pos]
    if "obb" in changes and changes["obb"] is not None:
        changes["obb"] = OBBGeometry(**changes["obb"])
    updated = current.model_copy(update=changes)
    anns[pos] = updated
    _autosave(image_id)
    return updated


@router.delete("/{image_id}/{ann_id}")
def delete_annotation(image_id: int, ann_id: int) -> dict:
    anns = _state.annotation_store.get(image_id, [])
    before = len(anns)
    _state.annotation_store[image_id] = [a for a in anns if a.id != ann_id]
    if len(_state.annotation_store[image_id]) == before:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    _autosave(image_id)
    return {"ok": True}


@router.delete("/{image_id}")
def clear_annotations(image_id: int) -> dict:
    _state.annotation_store.pop(image_id, None)
    _autosave(image_id)
    return {"ok": True}
