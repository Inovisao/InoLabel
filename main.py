"""Entry point desktop — inicia FastAPI em thread daemon e abre janela pywebview."""

from __future__ import annotations

import multiprocessing
import sys
import threading
import time

_HOST = "127.0.0.1"
_PORT = 7432


def _start_backend() -> None:
    import uvicorn
    from backend.main import app
    uvicorn.run(app, host=_HOST, port=_PORT, log_level="warning")


def _wait_for_server(timeout: float = 20.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{_HOST}:{_PORT}/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def main() -> int:
    # Necessario no Windows para processos spawned pelo PyInstaller
    multiprocessing.freeze_support()

    thread = threading.Thread(target=_start_backend, daemon=True)
    thread.start()

    if not _wait_for_server():
        print("[ERRO] Servidor nao iniciou a tempo.", file=sys.stderr)
        return 1

    try:
        import webview
    except ImportError:
        print(f"[INFO] pywebview nao instalado — acesse http://{_HOST}:{_PORT} no browser.")
        thread.join()
        return 0

    webview.create_window(
        "InoLabel",
        url=f"http://{_HOST}:{_PORT}",
        width=1400,
        height=900,
        min_size=(900, 600),
    )
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
