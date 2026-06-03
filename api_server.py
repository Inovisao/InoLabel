"""Entry point: start the FastAPI/uvicorn backend server."""

import os
import sys

import uvicorn

# PyInstaller windowed mode may leave stdout/stderr as None.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

if __name__ == "__main__":
    dev_mode = os.environ.get("INOLABEL_ENV", "production") == "development"
    uvicorn.run(
        "app.api.main:app",
        host="127.0.0.1",
        port=8765,
        reload=dev_mode,
        log_level="debug" if dev_mode else "info",
        log_config=None,
    )
