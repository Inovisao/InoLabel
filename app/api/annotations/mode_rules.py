"""Regras de cada modo sobre a anotação: o que o modo aceita e como a geometria fica coerente.

- detecção: só caixa; sem track_id.
- rastreamento: caixa + track_id (obrigatório quando vem do modelo).
- OBB: obb, cantos e bbox (envelope) sempre juntos; mover pelo bbox translada o obb.
- keypoint: pontos da classe; a bbox é o envelope dos pontos marcados.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.api.annotations.keypoints import validate_keypoints
from app.api.annotations.obb import finalize_obb, obb_from_bbox
from app.api.annotations.schemas import AnnotationUpsert
from app.api.common.errors import InvalidInput
from app.api.common.schemas import Annotation, OBBGeometry

Geometry = Tuple[List[float], Optional[OBBGeometry], Optional[list]]   # (bbox, obb, keypoints)


def check_new(session, body: AnnotationUpsert) -> None:
    """Recusa campos que o modo da sessão não usa."""
    if session.mode == "classification":
        raise InvalidInput("Classificacao nao usa bounding boxes; use /annotations/{image_id}/classification.")
    if session.mode == "detection" and body.track_id is not None:
        raise InvalidInput("Modo deteccao padrao nao aceita track_id.")
    if session.mode == "tracking" and body.source == "model" and body.track_id is None:
        raise InvalidInput("Modo rastreamento exige track_id para anotacoes geradas pelo modelo.")
    if session.mode == "keypoint" and (body.track_id is not None or body.obb is not None):
        raise InvalidInput("Modo keypoint não usa track_id nem obb.")
    if session.mode != "keypoint" and body.keypoints is not None:
        raise InvalidInput("keypoints so existe no modo keypoint.")
    if session.mode != "obb" and body.obb is not None:
        raise InvalidInput("obb so existe no modo OBB.")


def geometry_for_new(session, body: AnnotationUpsert, dims) -> Geometry:
    """Geometria final de uma anotação nova, conforme o modo. ``dims`` = (largura, altura)."""
    if session.mode == "keypoint":
        keypoints, bbox = validate_keypoints(session, body.category_id, body.keypoints, dims)
        return bbox, None, keypoints
    if session.mode == "obb":
        if body.obb is None:
            return body.bbox, obb_from_bbox(body.bbox), None
        obb, bbox = finalize_obb(body.obb)
        return bbox, obb, None
    return body.bbox, body.obb, None


def check_patch(session, changes: dict) -> None:
    """Recusa alterações inválidas antes de mexer na anotação."""
    if "category_id" in changes and not 0 <= int(changes["category_id"]) < len(session.classes):
        raise InvalidInput("category_id fora do intervalo de classes.")
    if changes.get("track_id") is not None and session.mode != "tracking":
        raise InvalidInput("track_id so existe no modo rastreamento.")
    if changes.get("track_id") is not None and changes["track_id"] < 0:
        raise InvalidInput("track_id deve ser >= 0.")
    if "bbox" in changes:
        bbox = changes["bbox"]
        if bbox is None or len(bbox) != 4 or bbox[2] <= 0 or bbox[3] <= 0:
            raise InvalidInput("bbox deve ser [x, y, largura, altura] com area.")
    if changes.get("keypoints") is not None and session.mode != "keypoint":
        raise InvalidInput("keypoints so existe no modo keypoint.")
    if changes.get("obb") is not None and session.mode != "obb":
        raise InvalidInput("obb so existe no modo OBB.")


def coherent_patch(session, current: Annotation, changes: dict, dims) -> dict:
    """Completa a alteração para a geometria continuar coerente no modo da sessão."""
    if session.mode == "keypoint":
        return _keypoint_patch(session, current, changes, dims)
    if session.mode == "obb":
        return _obb_patch(current, changes)
    return changes


def _keypoint_patch(session, current: Annotation, changes: dict, dims) -> dict:
    if changes.get("keypoints") is None and "category_id" not in changes:
        changes.pop("keypoints", None)
        changes.pop("bbox", None)   # a bbox do keypoint é sempre a dos pontos
        return changes
    # Trocar de classe só se a nova tiver o mesmo número de pontos.
    category = int(changes.get("category_id", current.category_id))
    points = changes["keypoints"] if changes.get("keypoints") is not None else current.keypoints
    changes["keypoints"], changes["bbox"] = validate_keypoints(session, category, points, dims)
    return changes


def _obb_patch(current: Annotation, changes: dict) -> dict:
    if changes.get("obb") is not None:
        # Edição de ângulo/posição: os parâmetros mandam, os cantos são recalculados.
        changes["obb"], changes["bbox"] = finalize_obb(OBBGeometry(**changes["obb"]), trust_points=False)
    elif "bbox" in changes and current.obb is not None:
        # Mover pelo retângulo (ferramenta V): translada o OBB, mantendo ângulo e tamanho.
        old_x, old_y, old_w, old_h = current.bbox
        new_x, new_y, new_w, new_h = changes["bbox"]
        dx = (new_x + new_w / 2.0) - (old_x + old_w / 2.0)
        dy = (new_y + new_h / 2.0) - (old_y + old_h / 2.0)
        moved = current.obb.model_copy(update={"cx": current.obb.cx + dx, "cy": current.obb.cy + dy})
        changes["obb"], changes["bbox"] = finalize_obb(moved, trust_points=False)
    else:
        changes.pop("obb", None)
    return changes
