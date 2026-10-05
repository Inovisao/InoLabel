"""Seletor nativo de pasta/arquivo — só funciona com o app rodando na máquina do usuário.

No Linux usa o seletor do próprio ambiente gráfico (zenity no GNOME, kdialog no KDE),
em um processo separado. O diálogo do Tkinter fica como último recurso: criado numa
thread do servidor e sob Wayland, ele abria em outro monitor ou atrás do navegador e
a tela ficava travada esperando por ele. No Windows e no macOS o diálogo do Tkinter
já é o nativo do sistema.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import List, Optional, Sequence, Tuple

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/browse", tags=["browse"])

FileTypes = Sequence[Tuple[str, str]]

FOLDER_TITLE = "Selecionar pasta"
FILE_TITLE = "Selecionar arquivo"


def _zenity_command(exe: str, *, folder: bool, filetypes: FileTypes) -> List[str]:
    cmd = [exe, "--file-selection", f"--title={FOLDER_TITLE if folder else FILE_TITLE}"]
    if folder:
        cmd.append("--directory")
    for label, pattern in filetypes:
        # zenity usa "*" para "todos"; "*.*" esconderia arquivos sem extensão.
        cmd.append(f"--file-filter={label} | {'*' if pattern == '*.*' else pattern}")
    return cmd


def _kdialog_command(exe: str, *, folder: bool, filetypes: FileTypes) -> List[str]:
    title = ["--title", FOLDER_TITLE if folder else FILE_TITLE]
    if folder:
        return [exe, *title, "--getexistingdirectory", "."]
    filters = "\n".join(f"{label} ({'*' if pattern == '*.*' else pattern})" for label, pattern in filetypes)
    return [exe, *title, "--getopenfilename", ".", filters or "*"]


def _native_command(*, folder: bool, filetypes: FileTypes) -> Optional[List[str]]:
    """Comando do seletor do ambiente gráfico no Linux; None se não houver nenhum."""
    if not sys.platform.startswith("linux"):
        return None
    for name, build in (("zenity", _zenity_command), ("kdialog", _kdialog_command)):
        exe = shutil.which(name)
        if exe:
            return build(exe, folder=folder, filetypes=filetypes)
    return None


def _run_native(cmd: List[str]) -> str:
    """Abre o seletor e devolve o caminho escolhido; cancelar ou falhar devolve ''."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return ""
    if result.returncode != 0:
        return ""  # 1 = usuário cancelou
    return result.stdout.strip()


def _tk_dialog(*, folder: bool, filetypes: FileTypes) -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    try:
        if folder:
            path = filedialog.askdirectory(title=FOLDER_TITLE)
        else:
            path = filedialog.askopenfilename(title=FILE_TITLE, filetypes=list(filetypes))
    finally:
        root.destroy()
    return path or ""


def _pick(*, folder: bool, filetypes: FileTypes = ()) -> str:
    cmd = _native_command(folder=folder, filetypes=filetypes)
    if cmd is not None:
        return _run_native(cmd)
    return _tk_dialog(folder=folder, filetypes=filetypes)


def _pick_folder() -> str:
    return _pick(folder=True)


def _pick_file(filetypes: FileTypes) -> str:
    return _pick(folder=False, filetypes=filetypes)


@router.get("/folder")
async def browse_folder() -> dict:
    path = await run_in_threadpool(_pick_folder)
    return {"path": path}


@router.get("/file")
async def browse_file(ext: str = "") -> dict:
    filetypes = (
        [("Modelo YOLO", "*.pt"), ("Todos os arquivos", "*.*")]
        if ext == "pt"
        else [("Todos os arquivos", "*.*")]
    )
    path = await run_in_threadpool(_pick_file, filetypes)
    return {"path": path}
