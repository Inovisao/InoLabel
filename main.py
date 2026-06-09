"""InoLabel — starts the FastAPI backend and opens the browser."""
import os
import sys
import threading
import time
import urllib.request
import webbrowser

# PyInstaller windowed mode sets sys.stdout/stderr to None; uvicorn's
# log formatter calls sys.stdout.isatty() and crashes without this guard.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import uvicorn

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def _open_browser() -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"{URL}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    webbrowser.open(URL)


if __name__ == "__main__":
    dev_mode = os.environ.get("INOLABEL_ENV", "production") == "development"

    # When running as a packaged .exe, set CWD to the exe's directory so that
    # relative paths like "outputs/" always resolve correctly regardless of how
    # the user launched the application.
    if not dev_mode and getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))

    threading.Thread(target=_open_browser, daemon=True).start()
    if dev_mode:
        # String reference required for --reload to work
        app_ref = "app.api.main:app"
    else:
        # Direct import so PyInstaller can trace and bundle the app package
        from app.api.main import app as _app
        app_ref = _app
    uvicorn.run(
        app_ref,
        host=HOST,
        port=PORT,
        reload=dev_mode,
        log_level="debug" if dev_mode else "info",
        log_config=None,
    )
