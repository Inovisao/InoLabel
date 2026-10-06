"""Pontos de cada classe no modo keypoint: os do pedido ou, ao retomar, os do projeto."""

from __future__ import annotations

from pathlib import Path

from app.api.common.errors import InvalidInput
from app.api.session import project_meta
from app.api.session.schemas import SessionStartRequest
from app.core.project_state.parser import keypoint_specs_from_payload


def resolve_keypoint_specs(req: SessionStartRequest, output_path: Path, project_data) -> list:
    """Pontos de cada classe: os enviados; ao retomar, os do projeto (COCO ou .inolabel.json).

    Recusa (422) classe sem pontos e mudança na quantidade de pontos de uma classe
    que já tem anotações — as instâncias antigas ficariam inválidas.
    """
    requested = {spec.name.strip(): spec for spec in req.keypoint_classes}
    from_project = keypoint_specs_from_payload(project_data, req.classes) if project_data else []
    from_meta = {
        str(c.get("name", "")).strip(): c
        for c in project_meta.read(output_path).get("keypoint_classes", []) or []
        if isinstance(c, dict)
    }

    counts_in_use: dict = {}
    if project_data:
        names_by_cat = {c.get("id"): str(c.get("name", "")).strip() for c in project_data.get("categories", []) or []}
        for ann in project_data.get("annotations", []) or []:
            name = names_by_cat.get(ann.get("category_id"))
            counts_in_use.setdefault(name, set()).add(len(ann.get("keypoints") or []) // 3)

    specs = []
    for pos, name in enumerate(req.classes):
        if name in requested:
            spec = {"keypoints": list(requested[name].keypoints), "skeleton": [list(l) for l in requested[name].skeleton]}
        elif pos < len(from_project) and from_project[pos]["keypoints"]:
            spec = from_project[pos]
        elif from_meta.get(name, {}).get("keypoints"):
            spec = {"keypoints": list(from_meta[name]["keypoints"]), "skeleton": list(from_meta[name].get("skeleton", []))}
        else:
            raise InvalidInput(f"Defina os pontos da classe '{name}' (modo keypoint).")
        in_use = counts_in_use.get(name, set()) - {0}
        if in_use and in_use != {len(spec["keypoints"])}:
            raise InvalidInput((
                    f"A classe '{name}' já tem anotações com {sorted(in_use)[0]} ponto(s); "
                    f"não dá para mudar para {len(spec['keypoints'])}."
                ))
        specs.append(spec)
    return specs
