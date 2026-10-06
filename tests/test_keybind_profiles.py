"""Persistência dos perfis web e migração dos arquivos antigos."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.keybinds import storage
from app.api.keybinds.router import router
from app.api.keybinds.schemas import KeybindProfiles


@pytest.fixture
def keybinds_file(tmp_path, monkeypatch):
    path = tmp_path / "keybinds.json"
    monkeypatch.setattr(storage, "KEYBINDS_PATH", path)
    return path


def test_profile_round_trip_and_legacy_route(keybinds_file):
    data = storage.DEFAULT_PROFILES.model_copy(deep=True)
    data.active_profile = "Meu perfil"
    data.profiles["Meu perfil"] = {key: list(value) for key, value in storage.DEFAULT_PROFILE.items()}
    data.profiles["Meu perfil"]["next_frame"] = ["J"]

    storage.save_profiles(data)

    assert storage.load_profiles() == data
    assert storage.load().binds["next_frame"] == "J"
    assert not keybinds_file.with_name("keybinds.tkinter.json").exists()


def test_migrates_all_tkinter_profiles_and_keeps_backup(keybinds_file):
    old = {"active_profile": "wasd", "profiles": {
        "arrows": {"next_frame": "Right", "prev_frame": "Left"},
        "wasd": {"next_frame": "d", "prev_frame": "a", "undo": "Control-z"},
    }}
    keybinds_file.write_text(json.dumps(old), encoding="utf-8")

    data = storage.load_profiles()
    assert data.active_profile == "wasd"
    assert data.profiles["arrows"]["next_frame"] == ["ArrowRight"]
    assert data.profiles["wasd"]["next_frame"] == ["D"]
    assert data.profiles["wasd"]["undo"] == ["Ctrl+Z"]

    storage.save_profiles(data)
    assert json.loads(keybinds_file.with_name("keybinds.tkinter.json").read_text()) == old


def test_rejects_conflicting_keys(keybinds_file):
    data = storage.DEFAULT_PROFILES.model_copy(deep=True)
    data.profiles["Custom"] = {key: list(value) for key, value in storage.DEFAULT_PROFILE.items()}
    data.profiles["Custom"]["tool_box"] = ["V"]
    with pytest.raises(ValueError, match="atribuída"):
        storage.save_profiles(data)
    assert not keybinds_file.exists()


def test_rejects_changes_to_default(keybinds_file):
    data = KeybindProfiles(active_profile="Padrão", profiles={"Padrão": {"next_frame": ["J"]}})
    with pytest.raises(ValueError, match="padrão"):
        storage.save_profiles(data)


def test_profiles_http_round_trip(keybinds_file):
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get("/api/keybinds/profiles")
    assert response.status_code == 200

    data = response.json()
    data["profiles"]["Custom"] = {key: list(value) for key, value in data["profiles"]["Padrão"].items()}
    data["profiles"]["Custom"]["next_frame"] = ["J"]
    data["active_profile"] = "Custom"
    assert client.put("/api/keybinds/profiles", json=data).status_code == 200
    assert client.get("/api/keybinds/profiles").json()["active_profile"] == "Custom"
    assert client.get("/api/keybinds").json()["binds"]["next_frame"] == "J"

    data["profiles"]["Custom"]["tool_box"] = ["V"]
    assert client.put("/api/keybinds/profiles", json=data).status_code == 422
