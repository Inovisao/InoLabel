"""Modo keypoint na API: sessão, anotação, persistência no COCO e exportação."""

import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.state import reset_state
from app.core.project_state.paths import state_path

W, H = 100, 80
QUAD = ["top_left", "top_right", "bottom_right", "bottom_left"]


@pytest.fixture()
def client(tmp_path):
    reset_state()
    data = tmp_path / "dataset"
    (data / "lote").mkdir(parents=True)
    for i in range(2):
        cv2.imwrite(str(data / "lote" / f"img_{i}.jpg"), np.zeros((H, W, 3), np.uint8))
    c = TestClient(app)
    yield c, data, tmp_path / "projeto"
    c.post("/api/session/stop")
    reset_state()


SPECS = [{"name": "placa", "keypoints": QUAD}, {"name": "olho", "keypoints": ["centro"]}]


def _start(c, data, out, specs=SPECS, classes=("placa", "olho")):
    r = c.post("/api/session/start", json={
        "mode": "keypoint", "data_path": str(data), "output_path": str(out),
        "classes": list(classes), "keypoint_classes": specs,
    })
    if r.status_code == 200:
        c.get("/api/frames/init")
    return r


def _quad(dx=0.0, v=2):
    return [[10 + dx, 10, v], [50 + dx, 10, v], [50 + dx, 40, v], [10 + dx, 40, v]]


# ── sessão ───────────────────────────────────────────────────────────────────

def test_session_requires_points_for_every_class(client):
    c, data, out = client
    r = _start(c, data, out, specs=[{"name": "placa", "keypoints": QUAD}])
    assert r.status_code == 422 and "olho" in r.json()["detail"]


def test_classes_expose_point_names(client):
    c, data, out = client
    assert _start(c, data, out).status_code == 200
    classes = c.get("/api/classes/").json()
    assert [cl["keypoints"] for cl in classes] == [QUAD, ["centro"]]


def test_modes_list_keypoint(client):
    c, _, _ = client
    assert "keypoint" in [m["id"] for m in c.get("/api/modes").json()]


# ── anotação ─────────────────────────────────────────────────────────────────

def test_instance_gets_envelope_bbox(client):
    c, data, out = client
    _start(c, data, out)
    pts = _quad()
    pts[2] = [0, 0, 0]          # ponto ausente não entra na bbox

    r = c.post("/api/annotations/0", json={"category_id": 0, "keypoints": pts})

    assert r.status_code == 200, r.text
    assert r.json()["bbox"] == [10, 10, 40, 30]
    assert r.json()["keypoints"][2] == [0, 0, 0]


@pytest.mark.parametrize("body", [
    {"category_id": 0, "keypoints": _quad()[:3]},                              # faltam pontos
    {"category_id": 0, "keypoints": [[0, 0, 0]] * 4},                           # nenhum marcado
    {"category_id": 0, "keypoints": [[10, 10, 2], [500, 10, 2], [5, 5, 2], [6, 6, 2]]},   # fora da imagem
    {"category_id": 0, "keypoints": [[10, 10, 3]] * 4},                        # visibilidade inválida
    {"category_id": 0, "keypoints": _quad(), "track_id": 1},                    # keypoint não usa track_id
])
def test_invalid_instances_are_rejected(client, body):
    c, data, out = client
    _start(c, data, out)
    assert c.post("/api/annotations/0", json=body).status_code == 422


def test_keypoints_outside_keypoint_mode_are_rejected(client):
    c, data, out = client
    c.post("/api/session/start", json={"mode": "detection", "data_path": str(data), "output_path": str(out), "classes": ["x"]})
    c.get("/api/frames/init")
    r = c.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 5, 5], "keypoints": [[1, 1, 2]]})
    assert r.status_code == 422


def test_moving_a_point_updates_the_bbox(client):
    c, data, out = client
    _start(c, data, out)
    ann = c.post("/api/annotations/0", json={"category_id": 0, "keypoints": _quad()}).json()
    pts = ann["keypoints"]
    pts[1] = [70, 5, 2]

    moved = c.patch(f"/api/annotations/0/{ann['id']}", json={"keypoints": pts}).json()

    assert moved["bbox"] == [10, 5, 60, 35]


def test_changing_class_needs_the_same_number_of_points(client):
    c, data, out = client
    _start(c, data, out)
    ann = c.post("/api/annotations/0", json={"category_id": 0, "keypoints": _quad()}).json()
    assert c.patch(f"/api/annotations/0/{ann['id']}", json={"category_id": 1}).status_code == 422


# ── persistência ─────────────────────────────────────────────────────────────

def test_reopening_restores_points_and_class_specs(client):
    c, data, out = client
    _start(c, data, out)
    c.post("/api/annotations/1", json={"category_id": 0, "keypoints": _quad(v=1)})
    c.post("/api/annotations/1", json={"category_id": 1, "keypoints": [[30, 30, 2]]})
    c.post("/api/session/stop")

    state = json.loads(state_path(out, "keypoint").read_text(encoding="utf-8"))
    assert state_path(out, "keypoint").name == "annotations_keypoints.coco.json"
    assert state["categories"][0]["keypoints"] == QUAD
    first, second = state["annotations"]
    assert first["keypoints"][:3] == [10, 10, 1] and first["num_keypoints"] == 4
    assert second["bbox"] == [30, 30, 0, 0]      # um ponto só: bbox sem área, mas válida

    # Retomar sem reenviar os pontos: vêm do próprio projeto.
    assert _start(c, data, out, specs=[]).status_code == 200
    loaded = c.get("/api/annotations/1").json()
    assert [a["keypoints"] for a in loaded] == [_quad(v=1), [[30, 30, 2]]]


def test_point_count_cannot_change_once_annotated(client):
    c, data, out = client
    _start(c, data, out)
    c.post("/api/annotations/0", json={"category_id": 0, "keypoints": _quad()})
    c.post("/api/session/stop")

    r = _start(c, data, out, specs=[{"name": "placa", "keypoints": QUAD[:3]}, {"name": "olho", "keypoints": ["centro"]}])
    assert r.status_code == 422 and "placa" in r.json()["detail"]


def test_txt_mirror_is_yolo_pose(client):
    c, data, out = client
    _start(c, data, out)
    c.post("/api/annotations/0", json={"category_id": 0, "keypoints": _quad()})
    values = (out / "labels" / "lote" / "img_0.txt").read_text(encoding="utf-8").split()
    assert len(values) == 1 + 4 + 3 * 4
    assert values[0] == "0" and values[5:8] == ["0.100000", "0.125000", "2"]


# ── exportação ───────────────────────────────────────────────────────────────

def test_export_yolo_pose_and_coco_keypoints(client, tmp_path):
    c, data, out = client
    _start(c, data, out)
    c.post("/api/annotations/0", json={"category_id": 0, "keypoints": _quad()})
    c.post("/api/annotations/0", json={"category_id": 1, "keypoints": [[30, 30, 2]]})
    session_id = c.get("/api/session/status").json()["session_id"]

    r = c.post("/api/export", json={"session_id": session_id, "destination": str(tmp_path / "exp"),
                                     "name": "ds", "formats": ["yolo", "coco"], "use_split": False})
    assert r.status_code == 200, r.text
    root = tmp_path / "exp" / "ds"

    assert "kpt_shape: [4, 3]" in (root / "data.yaml").read_text(encoding="utf-8")
    (label,) = (root / "labels").rglob("img_0.txt")
    lines = label.read_text(encoding="utf-8").strip().splitlines()
    assert [len(line.split()) for line in lines] == [17, 17]       # pontos completados até kpt_shape

    coco = json.loads((root / "_annotations.coco.json").read_text(encoding="utf-8"))
    assert coco["categories"][0]["keypoints"] == QUAD
    assert sorted(a["num_keypoints"] for a in coco["annotations"]) == [1, 4]
