"""Native file/folder picker via tkinter — only works on a local desktop machine."""
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/browse", tags=["browse"])


def _pick_folder() -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    path = filedialog.askdirectory(title="Selecionar pasta")
    root.destroy()
    return path or ""


def _pick_file(filetypes: list[tuple[str, str]]) -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    path = filedialog.askopenfilename(title="Selecionar arquivo", filetypes=filetypes)
    root.destroy()
    return path or ""


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
