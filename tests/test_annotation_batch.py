"""Anotações em lote: colar um bloco, mover o bloco e apagar a seleção (uma gravação só)."""

import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.annotations import service
from app.api.main import app
from app.api.state import reset_state
from app.core.project_state.paths import state_path


@pytest.fixture()
def client(tmp_path):
    reset_state()
    data = tmp_path / "dataset"
    data.mkdir()
    for i in range(3):
        cv2.imwrite(str(data / f"img_{i}.jpg"), np.zeros((100, 200, 3), np.uint8))
    c = TestClient(app)
    yield c, data, tmp_path / "projeto"
    c.post("/api/session/stop")
    reset_state()


def _start(c, data, out, mode="detection", **extra):
    body = {"mode": mode, "data_path": str(data), "output_path": str(out), "classes": ["a", "b"], **extra}
    r = c.post("/api/session/start", json=body)
    assert r.status_code == 200, r.text
    c.get("/api/frames/init")


def test_paste_block_creates_all_with_one_save(client, monkeypatch):
    c, data, out = client
    _start(c, data, out)
    saves = []
    monkeypatch.setattr(service, "autosave", lambda image_id: saves.append(image_id))
    block = [{"category_id": 0, "bbox": [10, 10, 20, 20]}, {"category_id": 1, "bbox": [50, 10, 20, 20]}]

    r = c.post("/api/annotations/1/batch", json={"annotations": block})

    assert r.status_code == 200, r.text
    created = r.json()["annotations"]
    assert [(a["category_id"], a["bbox"]) for a in created] == [(0, [10, 10, 20, 20]), (1, [50, 10, 20, 20])]
    assert len({a["id"] for a in created}) == 2
    assert saves == [1]


def test_paste_is_all_or_nothing(client):
    c, data, out = client
    _start(c, data, out)
    block = [{"category_id": 0, "bbox": [10, 10, 20, 20]}, {"category_id": 7, "bbox": [50, 10, 20, 20]}]

    assert c.post("/api/annotations/0/batch", json={"annotations": block}).status_code == 422
    assert c.get("/api/annotations/0").json() == []


def test_paste_in_tracking_keeps_ids_and_renumbers_repeated_ones(client):
    c, data, out = client
    _start(c, data, out, mode="tracking")
    c.post("/api/annotations/1", json={"category_id": 0, "bbox": [0, 0, 5, 5], "track_id": 3})
    block = [
        {"category_id": 0, "bbox": [10, 10, 20, 20], "track_id": 3},   # já existe no frame 1
        {"category_id": 0, "bbox": [40, 10, 20, 20], "track_id": 4},   # livre: mantém
    ]

    body = c.post("/api/annotations/1/batch", json={"annotations": block}).json()

    ids = [a["track_id"] for a in body["annotations"]]
    assert ids[1] == 4
    assert ids[0] not in (3, 4)
    assert body["renumbered_track_ids"] == 1


def test_paste_in_obb_keeps_angle(client):
    c, data, out = client
    _start(c, data, out, mode="obb")
    obb = {"cx": 50, "cy": 40, "width": 30, "height": 10, "angle": 30}
    created = c.post("/api/annotations/1/batch", json={"annotations": [{"category_id": 0, "obb": obb}]}).json()
    assert created["annotations"][0]["obb"]["angle"] == pytest.approx(30)


def test_move_block_updates_all_with_one_save_and_undo_data(client, monkeypatch):
    c, data, out = client
    _start(c, data, out)
    a = c.post("/api/annotations/0", json={"category_id": 0, "bbox": [10, 10, 20, 20]}).json()
    b = c.post("/api/annotations/0", json={"category_id": 1, "bbox": [50, 10, 20, 20]}).json()
    saves = []
    monkeypatch.setattr(service, "autosave", lambda image_id: saves.append(image_id))

    r = c.patch("/api/annotations/0/batch", json={"updates": [
        {"id": a["id"], "changes": {"bbox": [12, 13, 20, 20]}},
        {"id": b["id"], "changes": {"bbox": [52, 13, 20, 20]}},
    ]})

    assert r.status_code == 200, r.text
    assert [x["bbox"] for x in c.get("/api/annotations/0").json()] == [[12, 13, 20, 20], [52, 13, 20, 20]]
    assert saves == [0]


def test_move_block_with_unknown_id_changes_nothing(client):
    c, data, out = client
    _start(c, data, out)
    a = c.post("/api/annotations/0", json={"category_id": 0, "bbox": [10, 10, 20, 20]}).json()
    r = c.patch("/api/annotations/0/batch", json={"updates": [
        {"id": a["id"], "changes": {"bbox": [12, 13, 20, 20]}},
        {"id": 999, "changes": {"bbox": [1, 1, 5, 5]}},
    ]})
    assert r.status_code == 404
    assert c.get("/api/annotations/0").json()[0]["bbox"] == [10, 10, 20, 20]


def test_delete_selection_and_persist(client):
    c, data, out = client
    _start(c, data, out)
    ids = [c.post("/api/annotations/0", json={"category_id": 0, "bbox": [i * 30, 10, 20, 20]}).json()["id"] for i in range(3)]

    r = c.post("/api/annotations/0/batch-delete", json={"ids": ids[:2]})

    assert r.json() == {"ok": True, "removed": 2}
    assert [a["id"] for a in c.get("/api/annotations/0").json()] == [ids[2]]
    c.post("/api/session/stop")
    saved = json.loads(state_path(out, "detection").read_text(encoding="utf-8"))
    assert len(saved["annotations"]) == 1


def test_batch_routes_do_not_shadow_single_routes(client):
    c, data, out = client
    _start(c, data, out)
    a = c.post("/api/annotations/0", json={"category_id": 0, "bbox": [10, 10, 20, 20]}).json()
    assert c.patch(f"/api/annotations/0/{a['id']}", json={"category_id": 1}).status_code == 200
    assert c.post("/api/annotations/0/batch", json={"annotations": []}).status_code == 422
