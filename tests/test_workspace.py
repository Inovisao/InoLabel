"""Workspace de projetos (modelo Obsidian): pasta escolhida + índice + recentes."""

import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.state import reset_state
from app.core import workspace as ws


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "LOCAL_DIR", tmp_path / "local")
    reset_state()
    data = tmp_path / "guavira teste"            # espaço no caminho, como no uso real
    data.mkdir()
    cv2.imwrite(str(data / "a.jpg"), np.zeros((20, 30, 3), np.uint8))
    yield TestClient(app), tmp_path, data
    reset_state()


@pytest.mark.parametrize("name", ["", "  ", "..", "a/b", "a\\b", "con", "LPT1.txt", "nome.", 'x:"y'])
def test_invalid_project_names(name):
    with pytest.raises(ws.WorkspaceError):
        ws.validate_project_name(name)


def test_valid_project_name_with_accents_and_spaces():
    assert ws.validate_project_name("  Guavira Lote 1 ") == "Guavira Lote 1"


def test_index_is_rebuilt_when_missing(tmp_path, env):
    _, _, data = env
    root = tmp_path / "ws"
    ws.create_workspace(root)
    ws.create_project(root, name="p1", mode="detection", data_path=data, classes=["x"])
    ws.index_path(root).unlink()

    info = ws.load_workspace(root)

    assert [p["folder"] for p in info["projects"]] == ["p1"]
    assert ws.index_path(root).is_file()


def test_adopting_a_folder_keeps_existing_projects(tmp_path):
    root = tmp_path / "antigo"
    (root / "proj").mkdir(parents=True)
    (root / "proj" / ".inolabel.json").write_text(json.dumps({"mode": "tracking"}), encoding="utf-8")

    info = ws.create_workspace(root)

    assert info["projects"] == [{"folder": "proj", "name": "proj", "mode": "tracking", "created_at": ""}]


def test_relative_workspace_path_is_refused(env):
    client, _, _ = env
    r = client.post("/api/workspace", json={"path": "meus_projetos"})
    assert r.status_code == 422


def test_full_flow_create_project_start_session_and_list(env):
    client, tmp_path, data = env
    root = tmp_path / "inolabel"

    opened = client.post("/api/workspace", json={"path": str(root), "name": "Laboratório"}).json()
    assert opened["name"] == "Laboratório" and opened["projects"] == []

    created = client.post("/api/workspace/projects", json={
        "workspace": str(root), "name": "Lote 1", "mode": "detection", "data_path": str(data), "classes": ["fruto"],
    })
    assert created.status_code == 200, created.text
    out = created.json()["output_path"]
    assert out == str(root / "Lote 1")

    duplicate = client.post("/api/workspace/projects", json={
        "workspace": str(root), "name": "Lote 1", "mode": "detection", "data_path": str(data), "classes": ["fruto"],
    })
    assert duplicate.status_code == 422

    r = client.post("/api/session/start", json={"mode": "detection", "data_path": str(data), "output_path": out, "classes": ["fruto"]})
    assert r.status_code == 200
    meta = json.loads((root / "Lote 1" / ".inolabel.json").read_text(encoding="utf-8"))
    assert meta["name"] == "Lote 1"                 # início da sessão não apaga o nome
    client.post("/api/session/stop")

    listed = client.get("/api/workspace/projects", params={"path": str(root)}).json()
    assert [p["name"] for p in listed] == ["Lote 1"]

    overview = client.get("/api/workspace").json()
    assert overview["current"]["path"] == str(root.resolve())
    assert [r["path"] for r in overview["recent"]] == [str(root.resolve())]


def test_point_dataset_to_new_location(env):
    client, tmp_path, data = env
    root = tmp_path / "ws"
    client.post("/api/workspace", json={"path": str(root)})
    client.post("/api/workspace/projects", json={"workspace": str(root), "name": "p", "mode": "detection",
                                                 "data_path": str(data), "classes": ["x"]})
    moved = tmp_path / "dataset_movido"
    data.rename(moved)

    r = client.patch("/api/workspace/projects", json={"workspace": str(root), "folder": "p", "data_path": str(moved)})

    assert r.status_code == 200
    meta = json.loads((root / "p" / ".inolabel.json").read_text(encoding="utf-8"))
    assert meta["data_path"] == str(moved.resolve())
    bad = client.patch("/api/workspace/projects", json={"workspace": str(root), "folder": "p", "data_path": str(tmp_path / "nao_existe")})
    assert bad.status_code == 422


def test_recents_skip_deleted_workspaces(env):
    client, tmp_path, _ = env
    a, b = tmp_path / "a", tmp_path / "b"
    client.post("/api/workspace", json={"path": str(a)})
    client.post("/api/workspace", json={"path": str(b)})
    import shutil
    shutil.rmtree(b)

    overview = client.get("/api/workspace").json()

    assert overview["current"]["path"] == str(a.resolve())
    assert [(r["path"].endswith("/b"), r["exists"]) for r in overview["recent"]] == [(True, False), (False, True)]
