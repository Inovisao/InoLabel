"""Edição de anotações (PATCH, próximo ID) e classificação sem duplicar."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.state import reset_state
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


def _start(c, data, out, mode, classes=("a", "b")):
    r = c.post("/api/session/start", json={"mode": mode, "data_path": str(data), "output_path": str(out), "classes": list(classes)})
    assert r.status_code == 200, r.text
    c.get("/api/frames/init")


# ── edição ───────────────────────────────────────────────────────────────────

def test_patch_changes_class_and_track_id_and_persists(client):
    c, data, out = client
    _start(c, data, out, "tracking")
    ann = c.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 10, 10]}).json()

    r = c.patch(f"/api/annotations/0/{ann['id']}", json={"category_id": 1, "track_id": 12})

    assert r.status_code == 200
    assert (r.json()["category_id"], r.json()["track_id"]) == (1, 12)
    c.post("/api/session/stop")
    saved = json.loads(state_path(out, "tracking").read_text(encoding="utf-8"))["annotations"][0]
    assert (saved["category_id"], saved["track_id"]) == (2, 12)


def test_patch_omitted_fields_stay_and_null_clears_track_id(client):
    c, data, out = client
    _start(c, data, out, "tracking")
    ann = c.post("/api/annotations/0", json={"category_id": 1, "bbox": [1, 1, 10, 10], "track_id": 3}).json()

    moved = c.patch(f"/api/annotations/0/{ann['id']}", json={"bbox": [5, 5, 10, 10]}).json()
    assert (moved["category_id"], moved["track_id"], moved["bbox"]) == (1, 3, [5, 5, 10, 10])

    cleared = c.patch(f"/api/annotations/0/{ann['id']}", json={"track_id": None}).json()
    assert cleared["track_id"] is None


@pytest.mark.parametrize("mode,body", [
    ("tracking", {"category_id": 9}),
    ("detection", {"track_id": 4}),
    ("tracking", {"bbox": [1, 1, 0, 5]}),
])
def test_patch_rejects_invalid_changes(client, mode, body):
    c, data, out = client
    _start(c, data, out, mode)
    ann = c.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 10, 10]}).json()
    assert c.patch(f"/api/annotations/0/{ann['id']}", json=body).status_code == 422


def test_patch_unknown_annotation_is_404(client):
    c, data, out = client
    _start(c, data, out, "detection")
    assert c.patch("/api/annotations/0/999", json={"category_id": 0}).status_code == 404


def test_next_track_id_is_one_past_the_highest(client):
    c, data, out = client
    _start(c, data, out, "tracking")
    assert c.get("/api/annotations/next-track-id").json() == {"next_track_id": 1}
    c.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 5, 5], "track_id": 4})
    c.post("/api/annotations/1", json={"category_id": 0, "bbox": [1, 1, 5, 5], "track_id": 9})
    assert c.get("/api/annotations/next-track-id").json() == {"next_track_id": 10}


# ── classificação ────────────────────────────────────────────────────────────

def _files(out: Path):
    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*.jpg"))


def test_reclassifying_moves_instead_of_duplicating(client):
    """Regressão: a imagem ficava copiada nas duas pastas, em duas classes."""
    c, data, out = client
    _start(c, data, out, "classification", classes=("madura", "verde"))
    c.post("/api/annotations/0/classification", json={"category_id": 0})
    c.post("/api/annotations/0/classification", json={"category_id": 1})

    assert _files(out) == ["verde/img_0.jpg"]
    records = json.loads((out / "classification_state.json").read_text(encoding="utf-8"))["records"]
    assert [r["class_name"] for r in records] == ["verde"]


def test_frame_shows_its_current_class(client):
    c, data, out = client
    _start(c, data, out, "classification", classes=("madura", "verde"))
    assert c.post("/api/frames/goto/1").json()["classification_id"] is None
    c.post("/api/annotations/1/classification", json={"category_id": 1})

    frame = c.post("/api/frames/goto/1").json()
    assert frame["classification_id"] == 1 and frame["is_saved"] is True
    assert c.get("/api/annotations/1/classification").json() == {"image_id": 1, "class_id": 1, "class_name": "verde"}


def test_undo_removes_copy_and_record(client):
    c, data, out = client
    _start(c, data, out, "classification", classes=("madura", "verde"))
    c.post("/api/annotations/2/classification", json={"category_id": 0})

    r = c.delete("/api/annotations/2/classification")

    assert r.status_code == 200
    assert _files(out) == []
    assert c.post("/api/frames/goto/2").json()["classification_id"] is None
    assert c.delete("/api/annotations/2/classification").status_code == 404
    assert (data / "img_2.jpg").exists()      # original intacto


def test_project_listing_counts_classified_images(client):
    from app.api.projects.listing import list_projects

    c, data, out = client
    _start(c, data, out, "classification", classes=("madura", "verde"))
    c.post("/api/annotations/0/classification", json={"category_id": 0})
    c.post("/api/annotations/1/classification", json={"category_id": 1})
    c.post("/api/annotations/1/classification", json={"category_id": 0})   # reclassificar não conta duas vezes

    (entry,) = list_projects(str(out.parent))
    assert entry["annotated_frames"] == 2
