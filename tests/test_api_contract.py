from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from app.api.main import app

    return TestClient(app)


def test_api_import_does_not_load_tkinter():
    sys.modules.pop("app.api.main", None)
    sys.modules.pop("tkinter", None)

    importlib.import_module("app.api.main")

    assert "tkinter" not in sys.modules


def test_api_package_does_not_import_ui_modules():
    sys.modules.pop("app.api.main", None)
    for name in list(sys.modules):
        if name == "app.ui" or name.startswith("app.ui."):
            sys.modules.pop(name, None)

    importlib.import_module("app.api.main")

    assert not [name for name in sys.modules if name == "app.ui" or name.startswith("app.ui.")]


def test_modes_endpoint_returns_required_modes():
    response = _client().get("/api/modes")

    assert response.status_code == 200
    modes = response.json()
    assert [mode["id"] for mode in modes] == [
        "tracking",
        "detection",
        "obb",
        "classification",
    ]
    assert all({"id", "label", "description", "icon"} <= set(mode) for mode in modes)


def test_validate_path_rejects_missing_path():
    response = _client().post("/api/session/validate-path", json={"path": "Z:/missing/inolabel/path"})

    assert response.status_code == 422
    assert response.json()["valid"] is False
    assert "error" in response.json()


def test_validate_path_detects_folder_and_counts_files(tmp_path: Path):
    (tmp_path / "a.jpg").write_bytes(b"not a real image")
    (tmp_path / "b.txt").write_text("a.jpg\n", encoding="utf-8")

    response = _client().post("/api/session/validate-path", json={"path": str(tmp_path)})

    assert response.status_code == 200
    assert response.json() == {"valid": True, "type": "folder", "file_count": 2}


def test_validate_model_accepts_readable_pt_file(tmp_path: Path):
    model = tmp_path / "model.pt"
    model.write_bytes(b"x" * 1024 * 1024)

    response = _client().post("/api/session/validate-model", json={"path": str(model)})

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["size_mb"] == 1.0


def test_session_lifecycle_and_actions(tmp_path: Path):
    (tmp_path / "frame1.jpg").write_bytes(b"placeholder")
    (tmp_path / "frame2.jpg").write_bytes(b"placeholder")
    client = _client()

    start = client.post(
        "/api/session/start",
        json={
            "mode": "detection",
            "data_path": str(tmp_path),
            "output_path": str(tmp_path / "outputs"),
            "model_path": None,
            "resume": False,
            "classes": ["pessoa", "carro"],
        },
    )

    assert start.status_code == 200
    payload = start.json()
    assert payload["total_frames"] == 2
    assert payload["current_frame"] == 0
    session_id = payload["session_id"]

    status = client.get(f"/api/session/{session_id}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "running"

    action = client.post(f"/api/session/{session_id}/action", json={"action": "next"})
    assert action.status_code == 200
    assert action.json()["current_frame"] == 1

    stop = client.post(f"/api/session/{session_id}/stop")
    assert stop.status_code == 200
    assert "saved_frames" in stop.json()


def test_second_session_returns_conflict_while_running(tmp_path: Path):
    client = _client()
    body = {
        "mode": "detection",
        "data_path": str(tmp_path),
        "output_path": str(tmp_path / "outputs"),
        "model_path": None,
        "resume": False,
        "classes": ["pessoa"],
    }

    first = client.post("/api/session/start", json=body)
    assert first.status_code == 200

    second = client.post("/api/session/start", json=body)
    assert second.status_code == 409

    client.post(f"/api/session/{first.json()['session_id']}/stop")


def test_export_lifecycle(tmp_path: Path):
    client = _client()
    start = client.post(
        "/api/session/start",
        json={
            "mode": "detection",
            "data_path": str(tmp_path),
            "output_path": str(tmp_path / "outputs"),
            "model_path": None,
            "resume": False,
            "classes": ["pessoa"],
        },
    )
    session_id = start.json()["session_id"]

    export = client.post(
        "/api/export",
        json={
            "session_id": session_id,
            "destination": str(tmp_path),
            "name": "dataset",
            "formats": ["yolo", "coco"],
            "split": {"train": 0.7, "val": 0.2, "test": 0.1},
            "augmentation": False,
        },
    )

    assert export.status_code == 200
    progress = client.get(f"/api/export/{export.json()['export_id']}/progress")
    assert progress.status_code == 200
    assert 0.0 <= progress.json()["progress"] <= 1.0

    client.post(f"/api/session/{session_id}/stop")


def test_keybinds_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("INOLABEL_LOCAL_DIR", str(tmp_path))
    from app.api.routes import keybinds

    keybinds.KEYBINDS_PATH = tmp_path / "keybinds.json"
    client = _client()

    response = client.post(
        "/api/keybinds",
        json={"profile": "custom", "binds": {"validate": "Return", "next": "Right"}},
    )
    assert response.status_code == 200

    loaded = client.get("/api/keybinds")
    assert loaded.status_code == 200
    assert loaded.json()["profile"] == "custom"
    assert loaded.json()["binds"]["validate"] == "Return"


def test_config_paths_are_project_relative():
    import app.config as config

    assert config.OUTPUT_BASE == config.BASE_DIR / "outputs"
    assert config.ASSETS_DIR == config.BASE_DIR / "assets"
    assert config.LOCAL_DIR == config.BASE_DIR / ".local"
