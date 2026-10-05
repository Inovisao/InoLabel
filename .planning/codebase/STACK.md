# Technology Stack

**Analysis Date:** 2026-06-08

## Languages

**Primary:**
- Python 3.9 - Main application, FastAPI backend, Tkinter desktop tooling, computer vision, export pipelines, and test suite. Evidence: `.github/workflows/ci.yml`, `README.md`, `main.py`, `api_server.py`, `app/api/main.py`, `app/annotation/shared.py`, `tests/test_session_start_audit.py`.
- TypeScript 5.7.3 - React WebUI source and type-checked frontend build. Evidence: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/src/main.tsx`, `frontend/src/api/client.ts`.

**Secondary:**
- Rust 1.77.2 - Tauri v2 desktop shell that launches the Python FastAPI backend as a sidecar. Evidence: `frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/src/lib.rs`, `frontend/src-tauri/src/main.rs`.
- JavaScript/JSON - Frontend package metadata, Vite configuration, Tauri configuration, and browser build artifacts. Evidence: `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts`, `frontend/src-tauri/tauri.conf.json`.
- Shell/PowerShell - Cross-platform build scripts for PyInstaller packaging. Evidence: `build.sh`, `build.ps1`.

## Runtime

**Environment:**
- Python 3.9 is the supported application/test runtime. Use `python main.py` for the browser-opening local app and `python api_server.py` for the FastAPI backend entry point. Evidence: `.github/workflows/ci.yml`, `README.md`, `main.py`, `api_server.py`.
- Node.js 18 is used by CI for Node-based tasks; the frontend package is built with npm and Vite. Evidence: `.github/workflows/ci.yml`, `frontend/package.json`.
- Rust 1.77.2 is required for the Tauri shell. Evidence: `frontend/src-tauri/Cargo.toml`.

**Package Manager:**
- Python: `pip` installs unpinned dependencies from `requirements.txt`. Evidence: `README.md`, `.github/workflows/ci.yml`, `build.sh`, `build.ps1`.
- JavaScript: npm with lockfile version 3. Evidence: `frontend/package.json`, `frontend/package-lock.json`, `.github/workflows/ci.yml`.
- Rust: Cargo for Tauri crate dependencies. Evidence: `frontend/src-tauri/Cargo.toml`.
- Lockfile: `frontend/package-lock.json` present; Python dependency lockfile not detected; Rust `Cargo.lock` not detected by repository scan.

## Frameworks

**Core:**
- FastAPI - Local backend API and static frontend host. Evidence: `requirements.txt`, `app/api/main.py`, `app/api/routes/session.py`, `app/api/routes/export.py`.
- Uvicorn - ASGI server on `127.0.0.1:8765`, with reload controlled by `INOLABEL_ENV=development`. Evidence: `requirements.txt`, `main.py`, `api_server.py`.
- React 19 - Frontend UI framework for the WebUI. Evidence: `frontend/package.json`, `frontend/src/main.tsx`, `frontend/src/App.tsx`.
- Vite 6.1.0 - Frontend dev server/build pipeline, serving on port `5173` in development and proxying `/api` to FastAPI. Evidence: `frontend/package.json`, `frontend/vite.config.ts`.
- Tauri 2 - Native desktop shell that loads `frontend/dist` and starts `api_server` as a sidecar through the shell plugin. Evidence: `frontend/package.json`, `frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/tauri.conf.json`, `frontend/src-tauri/src/lib.rs`.
- Tkinter - Native desktop dialogs and legacy annotation UI components. Evidence: `README.md`, `app/api/routes/browse.py`, `app/annotation/shared.py`, `app/classification/tools/navigation.py`.
- PyInstaller - Windows/Linux executable packaging for the Python app and bundled frontend static files. Evidence: `InoLabel.spec`, `build.sh`, `build.ps1`, `README.md`.

**Testing:**
- pytest - CI invokes `python -m pytest -q`; several tests use pytest and FastAPI `TestClient`. Evidence: `.github/workflows/ci.yml`, `tests/test_session_start_audit.py`, `tests/test_export_improvements.py`.
- unittest - Many Python tests use the standard library `unittest` style. Evidence: `tests/test_dataset_export.py`, `tests/test_class_order.py`, `tests/test_obb_geometry.py`.
- FastAPI TestClient - API route testing. Evidence: `tests/test_export_improvements.py`, `tests/test_session_start_audit.py`.
- Playwright - CI runs demo Playwright tests under `.impeccable/demo`, not the main `frontend/` app. Evidence: `.github/workflows/ci.yml`.

**Build/Dev:**
- TypeScript compiler - `npm run build` executes `tsc && vite build`. Evidence: `frontend/package.json`, `frontend/tsconfig.json`.
- Tailwind CSS 4 via Vite plugin - Frontend styling pipeline. Evidence: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/styles.css`.
- PyInstaller collection hooks - `InoLabel.spec`, `build.sh`, and `build.ps1` collect `ultralytics`, `fastapi`, `starlette`, `uvicorn`, `app`, and `tracker`. Evidence: `InoLabel.spec`, `build.sh`, `build.ps1`.
- GitHub Actions - CI for Python dependency install/tests and demo Playwright tests. Evidence: `.github/workflows/ci.yml`.

## Key Dependencies

**Critical:**
- `ultralytics` unpinned - YOLO model loading/inference for detection and optional model-assisted annotation. Evidence: `requirements.txt`, `app/core/detector.py`, `app/annotation/state/core_init.py`.
- `opencv-python` unpinned - Image/video reading, frame encoding, geometry transforms, drawing/export image operations. Evidence: `requirements.txt`, `app/api/routes/frames.py`, `app/annotation/infrastructure/export/yolo_exporter.py`, `app/annotation/roi/roi_state.py`.
- `Pillow` unpinned - Tkinter image display and UI image handling. Evidence: `requirements.txt`, `app/annotation/shared.py`, `app/classification/tools/navigation.py`.
- `numpy` unpinned - Numeric geometry, frame arrays, tests, and tracking data. Evidence: `requirements.txt`, `app/models.py`, `app/geometry.py`, `tests/test_dataset_export.py`.
- `scipy` unpinned and `lapx` unpinned - Assignment/matching support for BYTETracker-style tracking. Evidence: `requirements.txt`, `tracker/matching.py`, `app/tracking/multiclass_byte_tracking.py`.
- `fastapi` unpinned - Backend API framework. Evidence: `requirements.txt`, `app/api/main.py`, `app/api/routes/*.py`.
- `uvicorn[standard]` unpinned - Backend ASGI runtime with standard extras. Evidence: `requirements.txt`, `main.py`, `api_server.py`.
- `react` `^19.0.0`, `react-dom` `^19.0.0` - Frontend rendering. Evidence: `frontend/package.json`, `frontend/src/main.tsx`.
- `zustand` `^5.0.3` - Frontend client state stores. Evidence: `frontend/package.json`, `frontend/src/stores/annotation.ts`, `frontend/src/stores/session.ts`.
- `konva` `^9.3.15` and `react-konva` `^19.0.0` - Canvas annotation UI. Evidence: `frontend/package.json`, `frontend/src/components/canvas/AnnotationCanvas.tsx`.
- `@radix-ui/react-*` packages - Dialog, dropdown, select, slider, switch, and tooltip primitives for the WebUI. Evidence: `frontend/package.json`, `frontend/src/components/modals/ExportModal.tsx`, `frontend/src/components/modals/ConfirmModal.tsx`.
- `lucide-react` `^0.475.0` - Frontend icons. Evidence: `frontend/package.json`, `frontend/src/components/layout/Topbar.tsx`, `frontend/src/pages/ProjectsPage.tsx`.

**Infrastructure:**
- `python-multipart` unpinned - FastAPI multipart compatibility; no source-level upload endpoint detected. Evidence: `requirements.txt`, `InoLabel.spec`.
- `websockets` unpinned - Uvicorn/websocket packaging support; no application websocket route detected. Evidence: `requirements.txt`, `InoLabel.spec`.
- `aiofiles` unpinned - Packaged with FastAPI/static serving support; no direct source import detected. Evidence: `requirements.txt`, `InoLabel.spec`.
- `filelock` unpinned - Packaged dependency; no direct source import detected in `app/` or `utils/`. Evidence: `requirements.txt`, `InoLabel.spec`.
- `python-jose[cryptography]` unpinned - Packaged dependency; no source-level JWT/auth flow detected. Evidence: `requirements.txt`, `InoLabel.spec`.
- `@tauri-apps/api` `^2`, `@tauri-apps/plugin-shell` `^2`, `tauri-plugin-shell` `2` - Tauri shell integration and Python sidecar spawning. Evidence: `frontend/package.json`, `frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/src/lib.rs`.
- `@vitejs/plugin-react` `^4.3.4`, `@tailwindcss/vite` `^4.0.0`, `tailwindcss` `^4.0.0`, `vite` `^6.1.0`, `typescript` `^5.7.3` - Frontend build stack. Evidence: `frontend/package.json`, `frontend/vite.config.ts`.

## Configuration

**Environment:**
- `INOLABEL_ENV=development` enables Uvicorn reload and debug logging. Evidence: `main.py`, `api_server.py`, `README.md`.
- `INOLABEL_OUTPUT_BASE` overrides the default output root. Evidence: `app/config.py`, `app/api/routes/validation.py`.
- `INOLABEL_ASSETS_DIR` overrides the asset directory. Evidence: `app/config.py`.
- `INOLABEL_LOCAL_DIR` overrides the local per-user state directory. Evidence: `app/config.py`, `app/api/routes/keybinds.py`.
- `CONF_THRESHOLD` controls YOLO detection confidence; default is `0.40`. Evidence: `app/config.py`, `README.md`.
- `SAVE_RECTIFIED_FRAMES` controls whether rectified frames are saved; default is false. Evidence: `app/config.py`, `README.md`.
- `MANUAL_IOU_THRESHOLD` controls manual/detection merge threshold; default is `0.30`. Evidence: `app/config.py`, `README.md`.
- Frontend environment variables are restricted to `VITE_` and `TAURI_ENV_*` prefixes. Evidence: `frontend/vite.config.ts`.
- `.env` files were not detected in the repository root scan.

**Build:**
- `frontend/vite.config.ts` configures React/Tailwind plugins, dev port `5173`, `/api` proxy to `http://127.0.0.1:8765`, `chrome105` build target, and Tauri debug minify/sourcemap behavior.
- `frontend/tsconfig.json` uses strict TypeScript with `ES2022`, `moduleResolution: "bundler"`, and React JSX transform.
- `frontend/src-tauri/tauri.conf.json` sets `frontendDist` to `../dist`, dev URL to `http://localhost:5173`, npm build/dev commands, and shell plugin settings.
- `frontend/src-tauri/Cargo.toml` pins Rust edition `2021`, minimum Rust `1.77.2`, and Tauri v2 dependencies.
- `InoLabel.spec` bundles `assets`, `frontend/dist`, Python hidden imports, collected dependency data, and the `main.py` entry point.
- `build.sh` and `build.ps1` require `frontend/dist` before packaging and install `requirements.txt` plus PyInstaller.
- `.github/workflows/ci.yml` installs Python dependencies, runs `python -m pytest -q || true`, and runs demo Playwright tests in `.impeccable/demo`.

## Platform Requirements

**Development:**
- Python 3.9 with Tkinter support. Evidence: `README.md`, `.github/workflows/ci.yml`.
- For Linux, install `python3-tk`, `build-essential`, `python3-dev`, `cmake`, and `git` for Tkinter and compiled dependency support. Evidence: `README.md`.
- For Windows, install Python 3.9, Visual C++ Build Tools, CMake, and optionally Git for compiled dependencies. Evidence: `README.md`.
- Node.js 18 and npm are used by CI; use `npm install`/`npm ci` under `frontend/` and `npm run build` before PyInstaller packaging. Evidence: `.github/workflows/ci.yml`, `frontend/package.json`, `build.ps1`, `build.sh`.
- Rust 1.77.2+ is required for Tauri shell builds. Evidence: `frontend/src-tauri/Cargo.toml`.

**Production:**
- Primary packaged target is a local desktop/browser application served from `127.0.0.1:8765`. Evidence: `main.py`, `api_server.py`, `app/api/main.py`.
- PyInstaller produces a self-contained `InoLabel` bundle; `model.pt` and `dataset/` must sit next to the executable and are not bundled. Evidence: `README.md`, `build.sh`, `build.ps1`, `app/config.py`.
- Tauri bundle target is configured as `all`, with the Python FastAPI backend expected as an `api_server` sidecar. Evidence: `frontend/src-tauri/tauri.conf.json`, `frontend/src-tauri/src/lib.rs`.

---

*Stack analysis: 2026-06-08*
