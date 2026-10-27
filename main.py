"""InoLabel — starts the FastAPI backend and opens the browser."""
import os
import sys
from pathlib import Path
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


def _open_browser(url: str = URL) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"{URL}/health", timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)
    print(f"A API não iniciou em {URL} dentro de 30 segundos. Verifique os erros no terminal.", file=sys.stderr)


def _frontend_ready(dev_mode: bool) -> bool:
    if dev_mode:
        return True
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    if (base / "frontend" / "dist" / "index.html").is_file():
        return True
    print(
        "Interface não compilada: frontend/dist/index.html não foi encontrado.\n"
        "Instale Node.js 20 ou superior e execute na pasta do projeto:\n"
        "  cd frontend\n"
        "  npm ci\n"
        "  npm run build\n"
        "  cd ..\n"
        "  python main.py",
        file=sys.stderr,
    )
    return False


if __name__ == "__main__":
    dev_mode = os.environ.get("INOLABEL_ENV", "production") == "development"
    if not _frontend_ready(dev_mode):
        sys.exit(1)

    # When running as a packaged .exe, set CWD to the exe's directory so that
    # relative paths like "outputs/" always resolve correctly regardless of how
    # the user launched the application.
    if not dev_mode and getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))

    browser_url = "http://localhost:5173" if dev_mode else URL
    if dev_mode:
        print("Inicie a interface em outro terminal: cd frontend && npm run dev", flush=True)
    threading.Thread(target=_open_browser, args=(browser_url,), daemon=True).start()
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
