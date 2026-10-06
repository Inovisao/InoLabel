"""Geometria de caixas orientadas (OBB): cantos, ângulo normalizado e envelope.

Funções puras, em pixels da imagem. Mesma convenção do exportador YOLO OBB."""

from __future__ import annotations

import math

from app.api.common.schemas import OBBGeometry


def points_from_obb(obb: OBBGeometry) -> list[list[float]]:
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


def normalize_angle(angle: float) -> float:
    """Ângulo em graus no intervalo (-180, 180]."""
    value = math.fmod(float(angle), 360.0)
    if value <= -180.0:
        value += 360.0
    elif value > 180.0:
        value -= 360.0
    return value


def envelope(points: list[list[float]]) -> list[float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]


def finalize_obb(obb: OBBGeometry, *, trust_points: bool = True) -> tuple[OBBGeometry, list[float]]:
    """Deixa o OBB consistente: ângulo normalizado, cantos recalculados e bbox = envelope.

    Com ``trust_points`` e 4 cantos válidos, os cantos mandam (estado salvo, modelo);
    sem eles — ou numa edição de ângulo/posição — mandam cx, cy, w, h e angle.
    """
    points = obb.points
    if trust_points and points is not None and len(points) == 4 and all(len(p) == 2 for p in points):
        base = obb_from_points([[float(x), float(y)] for x, y in points])
    else:
        base = obb.model_copy(update={"points": None})
    final = OBBGeometry(
        cx=float(base.cx),
        cy=float(base.cy),
        width=float(base.width),
        height=float(base.height),
        angle=normalize_angle(base.angle),
        angle_unit="degrees",
    )
    final.points = points_from_obb(final)
    return final, envelope(final.points)


def obb_from_bbox(bbox: list[float]) -> OBBGeometry:
    x, y, w, h = (float(value) for value in bbox)
    obb = OBBGeometry(
        cx=x + w / 2.0,
        cy=y + h / 2.0,
        width=w,
        height=h,
        angle=0.0,
        angle_unit="degrees",
    )
    obb.points = points_from_obb(obb)
    return obb


def obb_from_points(points: list[list[float]]) -> OBBGeometry:
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
