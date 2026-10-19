"""Editar classes durante a anotação: adicionar, renomear e remover (com reindexação)."""

import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.session.project_meta import META_FILE
from app.api.state import reset_state
from app.core.label_paths import label_path
from app.core.project_state.paths import state_path


@pytest.fixture()
def client(tmp_path):
    reset_state()
    data = tmp_path / "dataset"
    data.mkdir()
    for i in range(3):
        cv2.imwrite(str(data / f"img_{i}.jpg"), np.zeros((40, 60, 3), np.uint8))
    c = TestClient(app)
    yield c, data, tmp_path / "projeto"
    c.post("/api/session/stop")
    reset_state()


def _start(c, data, out, mode="detection", classes=("a", "b", "c"), **extra):
    body = {"mode": mode, "data_path": str(data), "output_path": str(out), "classes": list(classes), **extra}
    r = c.post("/api/session/start", json=body)
    assert r.status_code == 200, r.text
    c.get("/api/frames/init")


def _names(c):
    return [cls["name"] for cls in c.get("/api/classes/").json()]


def _saved(c, out, mode="detection"):
    c.post("/api/session/stop")  # espera o COCO em segundo plano
    return json.loads(state_path(out, mode).read_text(encoding="utf-8"))


def _txt(out, data, name):
    return label_path(out, data / name, data).read_text().split()


def test_add_class_mid_session_is_usable_and_persisted(client):
    c, data, out = client
    _start(c, data, out)

    r = c.post("/api/classes/", json={"name": "  nova "})

    assert r.status_code == 200
    assert [cls["name"] for cls in r.json()] == ["a", "b", "c", "nova"]
    ann = c.post("/api/annotations/0", json={"category_id": 3, "bbox": [1, 1, 10, 10]})
    assert ann.status_code == 200, ann.text
    meta = json.loads((out / META_FILE).read_text(encoding="utf-8"))
    assert meta["classes"] == ["a", "b", "c", "nova"]
    saved = _saved(c, out)
    assert [cat["name"] for cat in saved["categories"]] == ["a", "b", "c", "nova"]


def test_rename_keeps_ids_and_updates_coco(client):
    c, data, out = client
    _start(c, data, out)
    c.post("/api/annotations/0", json={"category_id": 1, "bbox": [1, 1, 10, 10]})

    r = c.patch("/api/classes/1", json={"name": "carro"})

    assert r.status_code == 200
    assert _names(c) == ["a", "carro", "c"]
    assert c.get("/api/annotations/0").json()[0]["category_id"] == 1
    saved = _saved(c, out)
    assert {cat["id"]: cat["name"] for cat in saved["categories"]}[saved["annotations"][0]["category_id"]] == "carro"


@pytest.mark.parametrize("name", ["", "   ", "A", "c"])
def test_rejects_empty_or_duplicate_names(client, name):
    c, data, out = client
    _start(c, data, out)
    assert c.post("/api/classes/", json={"name": name}).status_code == 422
    assert c.patch("/api/classes/1", json={"name": name}).status_code == 422
    assert _names(c)[0] == "a"


def test_remove_middle_class_deletes_its_annotations_and_shifts_the_rest(client):
    c, data, out = client
    _start(c, data, out)
    c.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 10, 10]})
    c.post("/api/annotations/0", json={"category_id": 1, "bbox": [2, 2, 10, 10]})
    c.post("/api/annotations/1", json={"category_id": 2, "bbox": [3, 3, 10, 10]})
    c.post("/api/annotations/2", json={"category_id": 1, "bbox": [4, 4, 10, 10]})

    usage = c.get("/api/classes/1/usage").json()
    assert (usage["annotations"], usage["frames"]) == (2, 2)

    r = c.delete("/api/classes/1")

    assert r.status_code == 200
    assert _names(c) == ["a", "c"]
    assert [a["category_id"] for a in c.get("/api/annotations/0").json()] == [0]
    assert [a["category_id"] for a in c.get("/api/annotations/1").json()] == [1]
    assert c.get("/api/annotations/2").json() == []
    # .txt espelho regravados com os ids novos
    assert _txt(out, data, "img_0.jpg")[0] == "0"
    assert _txt(out, data, "img_1.jpg")[0] == "1"
    assert _txt(out, data, "img_2.jpg") == []
    saved = _saved(c, out)
    names = {cat["id"]: cat["name"] for cat in saved["categories"]}
    assert sorted(names[a["category_id"]] for a in saved["annotations"]) == ["a", "c"]


def test_removed_class_survives_resume(client):
    c, data, out = client
    _start(c, data, out)
    c.post("/api/annotations/1", json={"category_id": 2, "bbox": [3, 3, 10, 10]})
    c.delete("/api/classes/0")
    c.post("/api/session/stop")

    meta = json.loads((out / META_FILE).read_text(encoding="utf-8"))
    assert meta["classes"] == ["b", "c"]
    _start(c, data, out, classes=meta["classes"], resume=True)
    ann = c.get("/api/annotations/1").json()[0]
    assert _names(c)[ann["category_id"]] == "c"


def test_cannot_remove_last_class_or_unknown_class(client):
    c, data, out = client
    _start(c, data, out, classes=("unica",))
    assert c.delete("/api/classes/0").status_code == 422
    assert c.delete("/api/classes/5").status_code == 404
    assert c.patch("/api/classes/5", json={"name": "x"}).status_code == 404


def test_keypoint_class_needs_point_names(client):
    c, data, out = client
    _start(c, data, out, mode="keypoint", classes=("pessoa",),
           keypoint_classes=[{"name": "pessoa", "keypoints": ["cabeca", "pe"]}])

    assert c.post("/api/classes/", json={"name": "gato"}).status_code == 422
    r = c.post("/api/classes/", json={"name": "gato", "keypoints": ["nariz", " cauda "]})

    assert r.status_code == 200
    assert r.json()[1]["keypoints"] == ["nariz", "cauda"]
    ann = c.post("/api/annotations/0", json={"category_id": 1, "bbox": [1, 1, 10, 10],
                                             "keypoints": [[2, 2, 2], [5, 5, 2]]})
    assert ann.status_code == 200, ann.text
    meta = json.loads((out / META_FILE).read_text(encoding="utf-8"))
    assert meta["keypoint_classes"][1] == {"name": "gato", "keypoints": ["nariz", "cauda"], "skeleton": []}


def test_classification_allows_only_adding(client):
    c, data, out = client
    _start(c, data, out, mode="classification", classes=("gato", "cachorro"))

    assert c.post("/api/classes/", json={"name": "passaro"}).status_code == 200
    assert [p for p in out.rglob("passaro") if p.is_dir()]
    assert c.patch("/api/classes/0", json={"name": "x"}).status_code == 422
    assert c.delete("/api/classes/0").status_code == 422
    assert _names(c) == ["gato", "cachorro", "passaro"]
