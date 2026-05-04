"""Helpers to open files or folders in the system file manager."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path


def reveal_path(target: Path) -> bool:
    """Open the file manager for ``target``, selecting the file when possible."""

    target = Path(target).expanduser()
    try:
        target = target.resolve()
    except OSError:
        target = target.absolute()
    folder = target if target.is_dir() else target.parent

    def _spawn(cmd: list[str]) -> bool:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:  # pylint: disable=broad-except
            return False

    if sys.platform.startswith("linux"):
        if target.is_file():
            for app in ("nautilus", "nemo", "dolphin"):
                exe = shutil.which(app)
                if exe and _spawn([exe, "--select", str(target)]):
                    return True
            thunar = shutil.which("thunar")
            if thunar and _spawn([thunar, str(target)]):
                return True

        for opener in ("gio", "xdg-open"):
            exe = shutil.which(opener)
            if not exe:
                continue
            cmd = [exe, "open", str(folder)] if opener == "gio" else [exe, str(folder)]
            if _spawn(cmd):
                return True
        return webbrowser.open(folder.as_uri())

    if sys.platform == "darwin":
        return _spawn(["open", "-R", str(target)]) if target.is_file() else _spawn(["open", str(folder)])

    if os.name == "nt":
        if target.is_file():
            return _spawn(["explorer", f"/select,{target}"])
        return _spawn(["explorer", str(folder)])

    return webbrowser.open(folder.as_uri())
