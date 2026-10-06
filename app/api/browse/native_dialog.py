"""Seletor nativo de pasta/arquivo — só funciona com o app rodando na máquina do usuário.

O seletor é sempre o do próprio sistema, aberto fora da thread do servidor quando
o sistema exige:

- Linux: zenity (GNOME) ou kdialog (KDE), em processo separado. O diálogo Tkinter,
  criado numa thread do servidor sob Wayland, abria em outro monitor ou atrás do
  navegador e travava a tela.
- macOS: ``osascript`` (choose folder / choose file), em processo separado. Lá o
  Tkinter só pode rodar na thread principal; numa thread do servidor ele derruba
  o processo.
- Windows: diálogo do Tkinter, que nesse sistema já é o seletor do Explorer e
  funciona a partir de uma thread de trabalho.

O Tkinter também é o último recurso no Linux sem zenity nem kdialog.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import List, Optional, Sequence, Tuple

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


def _osascript_command(exe: str, *, folder: bool, filetypes: FileTypes) -> List[str]:
    if folder:
        script = f'POSIX path of (choose folder with prompt "{FOLDER_TITLE}")'
    else:
        patterns = [pattern for _label, pattern in filetypes]
        # "of type" restringe a seleção; com "todos os arquivos" na lista não há restrição.
        extensions = [] if any(p in ("*", "*.*") for p in patterns) else [
            p.rsplit(".", 1)[-1] for p in patterns if "." in p
        ]
        of_type = " of type {" + ", ".join(f'"{ext}"' for ext in extensions) + "}" if extensions else ""
        script = f'POSIX path of (choose file with prompt "{FILE_TITLE}"{of_type})'
    return [exe, "-e", script]


def _native_command(*, folder: bool, filetypes: FileTypes) -> Optional[List[str]]:
    """Comando do seletor do sistema em processo separado; None quando o Tkinter é o caminho."""
    if sys.platform == "darwin":
        candidates = (("osascript", _osascript_command),)
    elif sys.platform.startswith("linux"):
        candidates = (("zenity", _zenity_command), ("kdialog", _kdialog_command))
    else:
        return None
    for name, build in candidates:
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
    path = result.stdout.strip()
    # osascript devolve pastas com "/" no fim.
    return path.rstrip("/") or path


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


def pick_folder() -> str:
    return _pick(folder=True)


def pick_file(filetypes: FileTypes) -> str:
    return _pick(folder=False, filetypes=filetypes)
