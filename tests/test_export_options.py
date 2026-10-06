"""Opções de exportação: augmentation (antes ignorada) e layout do COCO (Roboflow ou images/)."""

import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.state import reset_state


@pytest.fixture()
def session(tmp_path):
    reset_state()
    data = tmp_path / "dataset"
    data.mkdir()
    for i in range(4):
        img = np.full((48, 64, 3), 40 * i, np.uint8)
        cv2.imwrite(str(data / f"img_{i}.jpg"), img)
    client = TestClient(app)
    r = client.post("/api/session/start", json={"mode": "detection", "data_path": str(data),
                                                 "output_path": str(tmp_path / "proj"), "classes": ["x"]})
    sid = r.json()["session_id"]
    client.get("/api/frames/init")
    for i in range(4):
        client.post(f"/api/annotations/{i}", json={"category_id": 0, "bbox": [5, 5, 20, 20]})
    yield client, sid, tmp_path
    client.post("/api/session/stop")
    reset_state()


def _export(client, sid, dest, **options):
    body = {"session_id": sid, "destination": str(dest), "name": "ds", "formats": ["yolo"], "use_split": False, **options}
    r = client.post("/api/export", json=body)
    assert r.status_code == 200, r.text
    for _ in range(100):
        progress = client.get(f"/api/export/{r.json()['export_id']}/progress").json()
        if progress["status"] != "running":
            return progress
        time.sleep(0.05)
    raise AssertionError("exportação não terminou")


def test_augmentation_is_applied_to_yolo(session):
    client, sid, tmp = session
    progress = _export(client, sid, tmp / "exp", augmentation=True, augmentations=["flip_h", "brightness"], augmentation_copies=2)
    assert progress["status"] == "done", progress
    images = sorted(p.name for p in (tmp / "exp" / "ds" / "images" / "all").glob("*.jpg"))
    labels = sorted(p.name for p in (tmp / "exp" / "ds" / "labels" / "all").glob("*.txt"))
    assert len(images) == 4 * 3                       # original + 2 cópias
    assert any("_aug2" in n for n in images)
    assert len(labels) == len(images)


def test_augmentation_off_by_default(session):
    client, sid, tmp = session
    _export(client, sid, tmp / "exp")
    assert len(list((tmp / "exp" / "ds" / "images" / "all").glob("*.jpg"))) == 4


def test_unknown_augmentation_is_refused(session):
    client, sid, tmp = session
    r = client.post("/api/export", json={"session_id": sid, "destination": str(tmp / "exp"), "name": "ds",
                                         "formats": ["yolo"], "augmentation": True, "augmentations": ["teleporte"]})
    assert r.status_code == 422


def test_catalog_lists_available_augmentations(session):
    client, _, _ = session
    keys = {item["key"] for item in client.get("/api/export/augmentations").json()}
    assert {"flip_h", "brightness", "rotate"} <= keys


@pytest.mark.parametrize("layout,image_dir", [("roboflow", ""), ("images_dir", "images")])
def test_coco_layout(session, layout, image_dir):
    client, sid, tmp = session
    progress = _export(client, sid, tmp / "exp", formats=["coco"], coco_layout=layout, zip=True)
    assert progress["status"] == "done", progress
    root = tmp / "exp" / "ds"
    assert (root / "_annotations.coco.json").is_file()
    assert len(list((root / image_dir).glob("*.jpg")) if image_dir else list(root.glob("*.jpg"))) == 4
    assert Path(progress["zip_path"]).is_file()      # a conferência do zip aceita os dois layouts
