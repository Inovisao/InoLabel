"""InoLabel — starts the FastAPI backend and opens the browser."""
import os
import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def _open_browser() -> None:
    time.sleep(1.5)
    webbrowser.open(URL)


if __name__ == "__main__":
    dev_mode = os.environ.get("INOLABEL_ENV", "production") == "development"
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(
        "app.api.main:app",
        host=HOST,
        port=PORT,
        reload=dev_mode,
        log_level="debug" if dev_mode else "info",
    )
