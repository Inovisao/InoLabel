"""annotations.coco.json como estado do projeto (Parte A do plano)."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.core.coco_state import build_payload, parse_payload, state_path
from app.core.coco_state_writer import CocoStateWriter

W, H = 64, 48


def _frames(root: Path, names):
    paths = []
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), np.zeros((H, W, 3), np.uint8))
        paths.append(path)
    return sorted(paths)


def _ann(i, frame, bbox, cat=0, **extra):
    return {"id": i, "image_id": frame, "category_id": cat, "bbox": bbox, "source": "manual", **extra}


# ── build_payload ────────────────────────────────────────────────────────────

def test_payload_follows_the_1_0_contract(tmp_path):
    data = tmp_path / "ds"
    frames = _frames(data, ["lote_a/img.jpg", "lote_b/img.jpg"])
    payload = build_payload(
        mode="tracking", classes=["fruto", "folha"], data_path=data, frame_paths=frames,
        frame_dims={0: (W, H), 1: (W, H)},
        annotation_store={
            0: [_ann(5, 0, [50, 40, 30, 20], cat=1, track_id=7, score=0.9)],
            1: [_ann(6, 1, [100, 100, 5, 5])],          # totalmente fora: descartada
        },
    )
    assert [c["id"] for c in payload["categories"]] == [1, 2]
    assert [i["file_name"] for i in payload["images"]] == ["lote_a/img.jpg", "lote_b/img.jpg"]
    (ann,) = payload["annotations"]
    assert ann["category_id"] == 2
    assert ann["bbox"] == [50.0, 40.0, 14.0, 8.0]      # recortada à imagem
    assert ann["area"] == 14.0 * 8.0
    assert ann["track_id"] == 7 and ann["score"] == 0.9 and ann["source"] == "manual"
    assert payload["info"]["task_mode"] == "tracking"


def test_track_id_only_in_tracking_mode(tmp_path):
    frames = _frames(tmp_path, ["a.jpg"])
    payload = build_payload(
        mode="detection", classes=["x"], data_path=tmp_path, frame_paths=frames,
        frame_dims={0: (W, H)}, annotation_store={0: [_ann(1, 0, [1, 1, 5, 5], track_id=3)]},
    )
    assert "track_id" not in payload["annotations"][0]


def test_reviewed_frame_becomes_image_without_annotations(tmp_path):
    frames = _frames(tmp_path, ["a.jpg", "b.jpg", "c.jpg"])
    payload = build_payload(
        mode="detection", classes=["x"], data_path=tmp_path, frame_paths=frames,
        frame_dims={0: (W, H), 1: (W, H), 2: (W, H)},
        annotation_store={0: [_ann(1, 0, [1, 1, 5, 5])], 2: []}, reviewed={1},
    )
    assert [i["file_name"] for i in payload["images"]] == ["a.jpg", "b.jpg"]   # c: vazio e não revisado


def test_image_ids_are_stable_between_saves(tmp_path):
    frames = _frames(tmp_path, ["a.jpg", "b.jpg"])
    ids = {"b.jpg": 10}
    kwargs = dict(mode="detection", classes=["x"], data_path=tmp_path, frame_paths=frames,
                  frame_dims={0: (W, H), 1: (W, H)}, reviewed={0, 1}, annotation_store={}, image_ids=ids)
    first, second = build_payload(**kwargs), build_payload(**kwargs)
    assert {i["file_name"]: i["id"] for i in first["images"]} == {"a.jpg": 11, "b.jpg": 10}
    assert first["images"] == second["images"]


# ── parse_payload ────────────────────────────────────────────────────────────

def test_round_trip_keeps_track_id_source_score(tmp_path):
    data = tmp_path / "ds"
    frames = _frames(data, ["lote_a/img.jpg", "lote_b/img.jpg"])
    store = {1: [_ann(9, 1, [2, 2, 10, 10], cat=1, track_id=4, score=0.5, source="model")]}
    payload = build_payload(mode="tracking", classes=["a", "b"], data_path=data, frame_paths=frames,
                            frame_dims={0: (W, H), 1: (W, H)}, annotation_store=store, reviewed={0}, image_ids={})

    parsed = parse_payload(json.loads(json.dumps(payload)), frame_paths=frames, data_path=data, num_classes=2)

    (entry,) = parsed.annotations[1]
    assert (entry["category_id"], entry["track_id"], entry["score"], entry["source"]) == (1, 4, 0.5, "model")
    assert parsed.max_annotation_id == 9
    assert parsed.reviewed == {0}


def test_old_projects_with_bare_file_names_still_load(tmp_path):
    frames = _frames(tmp_path, ["lote_a/unica.jpg", "lote_a/rep.jpg", "lote_b/rep.jpg"])
    data = {
        "images": [{"id": 1, "file_name": "unica.jpg", "width": W, "height": H},
                   {"id": 2, "file_name": "rep.jpg", "width": W, "height": H}],
        "annotations": [_ann(1, 1, [1, 1, 5, 5], cat=1), _ann(2, 2, [1, 1, 5, 5], cat=1)],
        "categories": [{"id": 1, "name": "x"}],
    }
    parsed = parse_payload(data, frame_paths=frames, data_path=tmp_path, num_classes=1)
    unique_idx = frames.index(tmp_path / "lote_a/unica.jpg")
    assert list(parsed.annotations) == [unique_idx]
    assert parsed.unmatched_images == 1          # nome repetido: não dá para adivinhar


# ── escritor ─────────────────────────────────────────────────────────────────

def test_writer_keeps_only_the_latest_snapshot(tmp_path):
    writer = CocoStateWriter()
    target = tmp_path / "s" / "annotations.coco.json"
    for n in range(50):
        writer.submit(target, {"n": n})
    assert writer.flush(timeout=10)
    assert json.loads(target.read_text(encoding="utf-8")) == {"n": 49}
    assert not list(target.parent.glob("*.tmp"))


# ── fluxo pela API ───────────────────────────────────────────────────────────

@pytest.fixture()
def api(tmp_path):
    from fastapi.testclient import TestClient

    from app.api.main import app
    from app.api.state import reset_state

    reset_state()
    data = tmp_path / "dataset"
    _frames(data, ["lote_a/img_0.jpg", "lote_a/img_1.jpg", "lote_b/img_0.jpg"])
    client = TestClient(app)
    yield client, data, tmp_path / "projeto"
    client.post("/api/session/stop")
    reset_state()


def _start(client, data, out, mode="tracking"):
    r = client.post("/api/session/start", json={"mode": mode, "data_path": str(data),
                                                  "output_path": str(out), "classes": ["fruto", "folha"]})
    assert r.status_code == 200, r.text
    client.get("/api/frames/init")
    return r.json()


def test_track_id_survives_closing_and_reopening(api):
    client, data, out = api
    _start(client, data, out)
    client.post("/api/annotations/2", json={"category_id": 1, "bbox": [5, 5, 20, 20], "track_id": 7})
    client.post("/api/session/stop")

    state = json.loads(state_path(out, "tracking").read_text(encoding="utf-8"))
    assert state["annotations"][0]["track_id"] == 7
    assert state["images"][0]["file_name"] == "lote_b/img_0.jpg"

    _start(client, data, out)
    (ann,) = client.get("/api/annotations/2").json()
    assert ann["track_id"] == 7 and ann["category_id"] == 1


def test_project_without_coco_is_migrated_from_txt(api):
    client, data, out = api
    labels = out / "labels" / "lote_a"
    labels.mkdir(parents=True)
    (labels / "img_1.txt").write_text("1 0.5 0.5 0.25 0.25\n", encoding="utf-8")

    _start(client, data, out, mode="detection")
    client.post("/api/session/stop")

    state = json.loads(state_path(out, "detection").read_text(encoding="utf-8"))
    assert [i["file_name"] for i in state["images"]] == ["lote_a/img_1.jpg"]
    assert state["annotations"][0]["category_id"] == 2


def test_unreadable_state_refuses_session_and_keeps_file(api):
    client, data, out = api
    path = state_path(out, "detection")
    path.parent.mkdir(parents=True)
    path.write_text('{"images": [ truncado', encoding="utf-8")

    r = client.post("/api/session/start", json={"mode": "detection", "data_path": str(data),
                                                  "output_path": str(out), "classes": ["x"]})

    assert r.status_code == 422
    assert "annotations.coco.json" in r.json()["detail"]
    assert path.read_text(encoding="utf-8") == '{"images": [ truncado'


def test_backup_is_taken_when_session_opens(api):
    client, data, out = api
    _start(client, data, out, mode="detection")
    client.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 5, 5]})
    client.post("/api/session/stop")
    before = state_path(out, "detection").read_text(encoding="utf-8")

    _start(client, data, out, mode="detection")
    client.post("/api/annotations/1", json={"category_id": 0, "bbox": [1, 1, 5, 5]})
    client.post("/api/session/stop")

    bak = state_path(out, "detection").with_name("annotations.coco.json.bak")
    assert bak.read_text(encoding="utf-8") == before


def test_reviewed_negative_is_saved_and_exported(api):
    import asyncio

    from app.api.routes.export import _run_export
    from app.api.state import create_export
    from app.core.exporter import ExportJob

    client, data, out = api
    _start(client, data, out, mode="detection")
    client.post("/api/annotations/0", json={"category_id": 0, "bbox": [1, 1, 5, 5]})
    r = client.post("/api/annotations/1/reviewed", json={"reviewed": True})
    assert r.json() == {"image_id": 1, "reviewed": True, "annotation_count": 0}
    assert client.post("/api/frames/goto/1").json()["reviewed"] is True

    job = create_export(ExportJob(destination=out.parent / "exp", name="ds", formats=["yolo", "coco"], use_split=False))
    asyncio.run(_run_export(job.export_id))
    assert job.status == "done", job.current_file

    label = out.parent / "exp" / "ds" / "labels" / "all" / "lote_a" / "img_1.txt"
    assert label.is_file() and label.read_text(encoding="utf-8") == ""
    coco = json.loads((out.parent / "exp" / "ds" / "_annotations.coco.json").read_text(encoding="utf-8"))
    assert {c["id"] for c in coco["categories"]} == {1, 2}
    assert len(coco["images"]) == 2 and len(coco["annotations"]) == 1
