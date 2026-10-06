"""Regras das instâncias de keypoint: pontos por classe, visibilidade e envelope."""

from __future__ import annotations

from app.api.common.errors import InvalidInput


def keypoint_spec(session, category_id: int) -> list:
    specs = session.keypoint_specs or []
    return specs[category_id]["keypoints"] if 0 <= category_id < len(specs) else []


def validate_keypoints(session, category_id: int, keypoints, dims) -> tuple[list, list]:
    """Confere os pontos contra a classe e a imagem; devolve (pontos, bbox envelope).

    Quantidade igual à da classe, visibilidade 0/1/2, ao menos um ponto marcado e
    nenhum ponto marcado fora da imagem. dims = (largura, altura) do frame, ou None.
    """
    if not 0 <= category_id < len(session.classes):
        raise InvalidInput("category_id fora do intervalo de classes.")
    names = keypoint_spec(session, category_id)
    if keypoints is None or len(keypoints) != len(names):
        raise InvalidInput(f"A classe '{session.classes[category_id]}' tem {len(names)} ponto(s); recebidos {len(keypoints or [])}.")
    cleaned, placed = [], []
    for kp in keypoints:
        if len(kp) != 3 or int(kp[2]) not in (0, 1, 2):
            raise InvalidInput("Cada ponto é [x, y, v] com v = 0, 1 ou 2.")
        x, y, v = float(kp[0]), float(kp[1]), int(kp[2])
        if v == 0:
            cleaned.append([0.0, 0.0, 0])
            continue
        if dims is not None and not (-0.5 <= x <= dims[0] + 0.5 and -0.5 <= y <= dims[1] + 0.5):
            raise InvalidInput("Ponto fora da imagem.")
        if dims is not None:
            x, y = min(max(x, 0.0), float(dims[0])), min(max(y, 0.0), float(dims[1]))
        cleaned.append([x, y, v])
        placed.append((x, y))
    if not placed:
        raise InvalidInput("Instância sem nenhum ponto marcado.")
    xs = [p[0] for p in placed]
    ys = [p[1] for p in placed]
    return cleaned, [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
