# -*- mode: python ; coding: utf-8 -*-
"""
InoLabel PyInstaller spec file.

Build com:
    python build.py
ou diretamente:
    pyinstaller InoLabel.spec
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821  (SPECPATH injetado pelo PyInstaller)
FRONTEND_DIST = ROOT / "frontend" / "dist"

# ── Dados a empacotar ─────────────────────────────────────────────────────────
datas = [
    # Frontend React (build de producao)
    (str(FRONTEND_DIST), "frontend/dist"),
    # Assets (logo, icones)
    (str(ROOT / "assets"), "assets"),
]

# ── Binaries (cv2 e similares com arquivos .so/.pyd extras) ──────────────────
binaries = []

# ── Hidden imports necessarios ───────────────────────────────────────────────
hiddenimports = [
    # uvicorn
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # fastapi / starlette
    "starlette.routing",
    "starlette.staticfiles",
    "anyio",
    "anyio._backends._asyncio",
    # webview
    "webview",
    "webview.platforms.winforms",
    # numpy / scipy / cv2
    "numpy",
    "cv2",
    "scipy.special._ufuncs_cxx",
    "scipy.linalg.cython_blas",
    "scipy.linalg.cython_lapack",
    # lapx (Hungarian)
    "lapx",
    # backend packages
    "backend",
    "backend.api",
    "backend.services",
    "backend.annotation",
    "backend.annotation_obb",
    "backend.classification",
    "backend.core",
    "backend.tracker",
    "backend.tracking",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # UI frameworks nao usados
        "tkinter",
        "flet",
        # Testes e docs
        "pytest",
        "sphinx",
        # IPython / jupyter
        "IPython",
        "jupyter",
        "notebook",
        # Matplotlib (nao usada em producao)
        "matplotlib",
    ],
    noarchive=False,
    optimize=1,
)

# ── Coleta ultralytics (modelo YOLO — muitos arquivos dinamicos) ──────────────
from PyInstaller.utils.hooks import collect_all  # noqa: E402
ul_datas, ul_binaries, ul_hiddenimports = collect_all("ultralytics")
a.datas += ul_datas
a.binaries += ul_binaries
a.hiddenimports += ul_hiddenimports

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="InoLabel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                  # sem janela de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "inovisao.ico") if (ROOT / "assets" / "inovisao.ico").exists() else None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="InoLabel",
)
