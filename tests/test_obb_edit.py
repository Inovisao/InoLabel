"""Rotação e edição de caixas no modo OBB: obb, cantos e bbox sempre coerentes."""

import json
import math

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.state import reset_state
from app.core.project_state.paths import state_path

W, H = 200, 120


@pytest.fixture()
def client(tmp_path):
    reset_state()
    data = tmp_path / "dataset"
    data.mkdir()
    cv2.imwrite(str(data / "img_0.jpg"), np.zeros((H, W, 3), np.uint8))
    c = TestClient(app)
    yield c, data, tmp_path / "projeto"
    c.post("/api/session/stop")
    reset_state()


def _start(c, data, out, mode="obb"):
    r = c.post("/api/session/start", json={"mode": mode, "data_path": str(data), "output_path": str(out), "classes": ["navio"]})
    assert r.status_code == 200, r.text
    c.get("/api/frames/init")


def _flat(points):
    return [v for point in points for v in point]


def _new_box(c):
    return c.post("/api/annotations/0", json={"category_id": 0, "bbox": [60, 40, 40, 20]}).json()


def _rotated(obb, angle):
    return {**obb, "angle": angle, "points": obb["points"]}   # cantos antigos de propósito


def _corners(cx, cy, w, h, angle):
    t = math.radians(angle)
    c, s = math.cos(t), math.sin(t)
    return [[cx + dx * c - dy * s, cy + dx * s + dy * c] for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def test_rotating_recomputes_corners_and_envelope(client):
    c, data, out = client
    _start(c, data, out)
    ann = _new_box(c)

    r = c.patch(f"/api/annotations/0/{ann['id']}", json={"obb": _rotated(ann["obb"], 90)})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["obb"]["angle"] == pytest.approx(90)
    assert _flat(body["obb"]["points"]) == pytest.approx(_flat(_corners(80, 50, 40, 20, 90)))
    # Girada 90°, a caixa 40×20 vira um envelope 20×40 no mesmo centro.
    assert body["bbox"] == pytest.approx([70, 30, 20, 40])


@pytest.mark.parametrize("angle,expected", [(190, -170), (-180, 180), (540, 180), (-30, -30)])
def test_angle_is_normalized(client, angle, expected):
    c, data, out = client
    _start(c, data, out)
    ann = _new_box(c)
    body = c.patch(f"/api/annotations/0/{ann['id']}", json={"obb": _rotated(ann["obb"], angle)}).json()
    assert body["obb"]["angle"] == pytest.approx(expected)


def test_moving_by_bbox_moves_the_rotated_box(client):
    """Regressão: mover com a ferramenta V mudava só o bbox; o obb exportado ficava parado."""
    c, data, out = client
    _start(c, data, out)
    ann = _new_box(c)
    rotated = c.patch(f"/api/annotations/0/{ann['id']}", json={"obb": _rotated(ann["obb"], 30)}).json()
    x, y, w, h = rotated["bbox"]

    moved = c.patch(f"/api/annotations/0/{ann['id']}", json={"bbox": [x + 10, y - 5, w, h]}).json()

    assert (moved["obb"]["cx"], moved["obb"]["cy"]) == pytest.approx((90, 45))
    assert moved["obb"]["angle"] == pytest.approx(30)
    assert moved["bbox"] == pytest.approx([x + 10, y - 5, w, h])


def test_obb_outside_obb_mode_is_rejected(client):
    c, data, out = client
    _start(c, data, out, mode="detection")
    ann = c.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 10, 10]}).json()
    obb = {"cx": 6, "cy": 6, "width": 10, "height": 10, "angle": 15}
    assert c.patch(f"/api/annotations/0/{ann['id']}", json={"obb": obb}).status_code == 422
    assert c.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 10, 10], "obb": obb}).status_code == 422


def test_rotation_survives_reopening_the_project(client):
    c, data, out = client
    _start(c, data, out)
    ann = _new_box(c)
    c.patch(f"/api/annotations/0/{ann['id']}", json={"obb": _rotated(ann["obb"], 45)})
    c.post("/api/session/stop")

    saved = json.loads(state_path(out, "obb").read_text(encoding="utf-8"))["annotations"][0]
    assert saved["obb"]["angle"] == pytest.approx(45)

    _start(c, data, out)
    (loaded,) = c.get("/api/annotations/0").json()
    assert loaded["obb"]["angle"] == pytest.approx(45)
    assert _flat(loaded["obb"]["points"]) == pytest.approx(_flat(_corners(80, 50, 40, 20, 45)))


def test_exported_yolo_obb_line_has_the_rotated_corners(client, tmp_path):
    c, data, out = client
    _start(c, data, out)
    ann = _new_box(c)
    c.patch(f"/api/annotations/0/{ann['id']}", json={"obb": _rotated(ann["obb"], 90)})
    session_id = c.get("/api/session/status").json()["session_id"]

    r = c.post("/api/export", json={"session_id": session_id, "destination": str(tmp_path / "exp"),
                                     "name": "ds", "formats": ["yolo"], "use_split": False})
    assert r.status_code == 200, r.text

    (label,) = (tmp_path / "exp" / "ds" / "labels").rglob("img_0.txt")
    values = [float(v) for v in label.read_text(encoding="utf-8").split()[1:]]
    expected = [v for x, y in _corners(80, 50, 40, 20, 90) for v in (x / W, y / H)]
    assert values == pytest.approx(expected, abs=1e-5)
