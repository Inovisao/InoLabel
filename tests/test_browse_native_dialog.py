"""O seletor de pasta/arquivo usa o diálogo do ambiente gráfico no Linux.

Regressão: o diálogo era um Tkinter criado numa thread do servidor; sob Wayland
abria em outro monitor ou atrás do navegador e travava a tela.
"""

from types import SimpleNamespace

import pytest

from app.api.routes import browse

YOLO_TYPES = [("Modelo YOLO", "*.pt"), ("Todos os arquivos", "*.*")]


@pytest.fixture()
def linux(monkeypatch):
    monkeypatch.setattr(browse.sys, "platform", "linux")


def _available(monkeypatch, *names):
    monkeypatch.setattr(browse.shutil, "which", lambda name: f"/usr/bin/{name}" if name in names else None)


def _fake_run(monkeypatch, *, returncode=0, stdout=""):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=returncode, stdout=stdout)

    monkeypatch.setattr(browse.subprocess, "run", run)
    return calls


def _forbid_tk(monkeypatch):
    def boom(**kwargs):
        raise AssertionError("o diálogo Tkinter não deveria ser usado")

    monkeypatch.setattr(browse, "_tk_dialog", boom)


def test_folder_uses_zenity_and_returns_the_chosen_path(linux, monkeypatch):
    _available(monkeypatch, "zenity", "kdialog")
    _forbid_tk(monkeypatch)
    calls = _fake_run(monkeypatch, stdout="/home/u/meu dataset\n")

    assert browse._pick_folder() == "/home/u/meu dataset"
    assert calls == [["/usr/bin/zenity", "--file-selection", "--title=Selecionar pasta", "--directory"]]


def test_file_passes_filters_to_zenity(linux, monkeypatch):
    _available(monkeypatch, "zenity")
    _forbid_tk(monkeypatch)
    calls = _fake_run(monkeypatch, stdout="/m/best.pt\n")

    assert browse._pick_file(YOLO_TYPES) == "/m/best.pt"
    assert "--directory" not in calls[0]
    assert "--file-filter=Modelo YOLO | *.pt" in calls[0]
    assert "--file-filter=Todos os arquivos | *" in calls[0]


def test_cancelling_returns_empty_path(linux, monkeypatch):
    _available(monkeypatch, "zenity")
    _forbid_tk(monkeypatch)
    _fake_run(monkeypatch, returncode=1, stdout="")

    assert browse._pick_folder() == ""


def test_kdialog_is_used_when_zenity_is_missing(linux, monkeypatch):
    _available(monkeypatch, "kdialog")
    _forbid_tk(monkeypatch)
    calls = _fake_run(monkeypatch, stdout="/dados\n")

    assert browse._pick_folder() == "/dados"
    assert calls[0][0] == "/usr/bin/kdialog"
    assert "--getexistingdirectory" in calls[0]


def test_falls_back_to_tk_only_without_any_native_tool(linux, monkeypatch):
    _available(monkeypatch)
    monkeypatch.setattr(browse, "_tk_dialog", lambda **kwargs: "/via/tk")

    assert browse._pick_folder() == "/via/tk"


@pytest.fixture()
def macos(monkeypatch):
    monkeypatch.setattr(browse.sys, "platform", "darwin")


def test_macos_folder_uses_osascript_never_tk(macos, monkeypatch):
    """No macOS o Tkinter fora da thread principal derruba o processo."""
    _available(monkeypatch, "osascript")
    _forbid_tk(monkeypatch)
    calls = _fake_run(monkeypatch, stdout="/Users/u/meu dataset/\n")

    assert browse._pick_folder() == "/Users/u/meu dataset"
    assert calls == [[
        "/usr/bin/osascript", "-e", 'POSIX path of (choose folder with prompt "Selecionar pasta")',
    ]]


def test_macos_file_restricts_type_only_without_all_files_option(macos, monkeypatch):
    _available(monkeypatch, "osascript")
    _forbid_tk(monkeypatch)
    calls = _fake_run(monkeypatch, stdout="/Users/u/best.pt\n")

    assert browse._pick_file([("Modelo YOLO", "*.pt")]) == "/Users/u/best.pt"
    assert calls[0][2] == 'POSIX path of (choose file with prompt "Selecionar arquivo" of type {"pt"})'

    browse._pick_file(YOLO_TYPES)   # inclui "Todos os arquivos"
    assert "of type" not in calls[1][2]


def test_macos_cancel_returns_empty_path(macos, monkeypatch):
    _available(monkeypatch, "osascript")
    _forbid_tk(monkeypatch)
    _fake_run(monkeypatch, returncode=1)

    assert browse._pick_folder() == ""


def test_windows_keeps_the_tk_dialog(monkeypatch):
    """No Windows o diálogo do Tkinter já é o seletor do Explorer."""
    monkeypatch.setattr(browse.sys, "platform", "win32")
    _available(monkeypatch, "zenity")
    monkeypatch.setattr(browse, "_tk_dialog", lambda **kwargs: "C:/dados")

    assert browse._pick_folder() == "C:/dados"


def test_launch_failure_does_not_raise(linux, monkeypatch):
    _available(monkeypatch, "zenity")
    _forbid_tk(monkeypatch)

    def run(cmd, **kwargs):
        raise OSError("sem display")

    monkeypatch.setattr(browse.subprocess, "run", run)

    assert browse._pick_folder() == ""
