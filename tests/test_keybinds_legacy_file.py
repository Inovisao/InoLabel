"""A rota de atalhos precisa conviver com o keybinds.json deixado pelo app Tkinter 1.0."""

import json

import pytest

from app.api.routes import keybinds

LEGACY = {
    "active_profile": "wasd",
    "profiles": {
        "arrows": {"next_frame": "Right", "prev_frame": "Left"},
        "wasd": {"next_frame": "d", "prev_frame": "a", "toggle_selection": ""},
    },
}


@pytest.fixture()
def keybinds_file(tmp_path, monkeypatch):
    path = tmp_path / "keybinds.json"
    monkeypatch.setattr(keybinds, "KEYBINDS_PATH", path)
    return path


def test_missing_file_returns_default(keybinds_file):
    assert keybinds.get_keybinds() == keybinds.DEFAULT_KEYBINDS


def test_legacy_tkinter_file_is_read_as_active_profile(keybinds_file):
    keybinds_file.write_text(json.dumps(LEGACY), encoding="utf-8")

    profile = keybinds.get_keybinds()

    assert profile.profile == "wasd"
    assert profile.binds == {"next_frame": "d", "prev_frame": "a"}  # atalho vazio fica de fora


@pytest.mark.parametrize("content", ["{ truncado", "[1, 2]", '{"profiles": {}, "active_profile": "x"}'])
def test_unreadable_file_falls_back_to_default(keybinds_file, content):
    keybinds_file.write_text(content, encoding="utf-8")
    assert keybinds.get_keybinds() == keybinds.DEFAULT_KEYBINDS


def test_saving_over_legacy_file_keeps_a_copy(keybinds_file):
    keybinds_file.write_text(json.dumps(LEGACY), encoding="utf-8")
    new_profile = keybinds.KeybindProfile(profile="custom", binds={"validate": "space"})

    keybinds.save_keybinds(new_profile)

    backup = keybinds_file.with_name("keybinds.tkinter.json")
    assert json.loads(backup.read_text(encoding="utf-8")) == LEGACY
    assert keybinds.get_keybinds() == new_profile


def test_saving_twice_does_not_replace_the_legacy_copy(keybinds_file):
    keybinds_file.write_text(json.dumps(LEGACY), encoding="utf-8")
    keybinds.save_keybinds(keybinds.KeybindProfile(profile="a", binds={}))
    keybinds.save_keybinds(keybinds.KeybindProfile(profile="b", binds={}))

    backup = keybinds_file.with_name("keybinds.tkinter.json")
    assert json.loads(backup.read_text(encoding="utf-8")) == LEGACY
    assert keybinds.get_keybinds().profile == "b"
