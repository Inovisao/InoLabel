# Technology Stack

**Analysis Date:** 2026-05-29

## Languages

**Primary:**
- Python 3.9+ - Backend API, desktop launcher, computer-vision annotation tools, dataset exporters, and tests in `main.py`, `backend/main.py`, `backend/annotation/tool.py`, `backend/annotation_obb/tool.py`, `backend/services/classification_service.py`, `backend/dataset_export.py`, `utils/`, and `tests/`. The `README.md` specifies Python 3.9+ via conda.
- TypeScript/TSX - React frontend in `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/lib/`, and `frontend/src/stores/`.

**Secondary:**
- JavaScript - Frontend tooling config in `frontend/eslint.config.js`.
- PyInstaller spec Python - Desktop bundle definition in `InoLabel.spec`.
- CSS - Tailwind CSS entry and design tokens in `frontend/src/index.css`.

## Runtime

**Environment:**
- CPython 3.9+ - Required by `README.md`; backend launches with `python main.py` and `python -m uvicorn backend.main:app` from `build.py`.
- Node.js - Required for the frontend Vite toolchain in `frontend/package.json`; no `.nvmrc`, `engines`, or repo-pinned Node version detected.
- Browser/WebView runtime - Production desktop mode opens the local FastAPI app in pywebview from `main.py`; development mode uses a browser at `http://localhost:5173` per `build.py`.

**Package Manager:**
- Python package manager: conda/pip-compatible `requirements.txt`; `README.md` documents `conda install -c conda-forge --file requirements.txt`.
- Python lockfile: missing; versions are unpinned in `requirements.txt`.
- Frontend package manager: npm, based on `frontend/package-lock.json` and scripts in `frontend/package.json`.
- Frontend lockfile: present at `frontend/package-lock.json`.

## Frameworks

**Core:**
- FastAPI - HTTP API and WebSocket server in `backend/main.py`, with routers in `backend/api/session.py`, `backend/api/frame.py`, `backend/api/export.py`, `backend/api/wizard.py`, and `backend/api/ws.py`.
- Uvicorn - ASGI runtime launched from `main.py` and `build.py`.
- React 19.2.6 - Frontend application mounted in `frontend/src/main.tsx` and routed between wizard/layout views in `frontend/src/App.tsx`.
- Vite 8.0.12 - Frontend dev server and production build in `frontend/package.json` and `frontend/vite.config.ts`.
- Tailwind CSS 4.3.0 - Styling pipeline configured through `@tailwindcss/vite` in `frontend/vite.config.ts` and imported from `frontend/src/index.css`.
- pywebview - Optional desktop shell created in `main.py`; falls back to browser access if import fails.

**Testing:**
- Python `unittest` - Test files under `tests/` define `unittest.TestCase` classes and can be discovered with `python -m unittest discover tests`.
- pytest cache is ignored in `.gitignore`, but pytest is not listed in `requirements.txt` and no pytest config was detected.
- Frontend test framework: not detected. `frontend/package.json` has no `test` script and no Vitest/Jest/Playwright dependency.

**Build/Dev:**
- TypeScript 6.0.2 - Frontend type checking via `tsc -b` in `frontend/package.json`; project references in `frontend/tsconfig.json`.
- ESLint 10.3.0 - Frontend linting via `npm run lint`; config at `frontend/eslint.config.js`.
- PyInstaller - Desktop packaging via `build.py` and `InoLabel.spec`; PyInstaller is required for packaging but is not listed in `requirements.txt`.
- OpenCV/Pillow/NumPy/SciPy/lapx/Ultralytics - Computer-vision stack used across `backend/annotation/`, `backend/annotation_obb/`, `backend/tracker/`, and `backend/annotation/core/augmentation/`.

## Key Dependencies

**Critical:**
- `fastapi` - Owns API routing, validation, HTTP errors, and WebSocket endpoint in `backend/main.py` and `backend/api/`.
- `uvicorn[standard]` - Runs the local API server from `main.py` and `build.py`.
- `ultralytics` - Loads YOLO models in `backend/annotation/state/core_init.py`; optional model weights are supplied by the user through session configuration.
- `opencv-python` (`cv2`) - Video/image IO, ROI homography, drawing, augmentation, and export image writes in `backend/annotation/sources/source_helpers.py`, `backend/annotation/roi/roi_state.py`, `backend/annotation/infrastructure/export/yolo_exporter.py`, and `backend/annotation/core/augmentation/augmentation_service.py`.
- `numpy` - Detection arrays and geometry operations in `backend/models.py`, `backend/geometry.py`, and annotation modules.
- `scipy` and `lapx` - BYTETracker matching and assignment in `backend/tracker/matching.py` and `tracker/matching.py`.
- `Pillow` - Image loading/conversion for classification in `backend/services/classification_service.py` and legacy utilities in `utils/annotation_tool_bytetracked.py`.
- `websockets` - Uvicorn/WebSocket runtime support for `backend/api/ws.py`.
- `python-multipart` - Multipart/form support dependency listed in `requirements.txt`, though no upload endpoint was detected in `backend/api/`.
- `pywebview` - Desktop window host used by `main.py`.

**Infrastructure:**
- `@tanstack/react-query` 5.100.14 - Installed frontend dependency in `frontend/package.json`; no active import detected under `frontend/src/`.
- `axios` 1.16.1 - HTTP client wrapper in `frontend/src/lib/api.ts`.
- `zustand` 5.0.14 - Client state stores in `frontend/src/stores/sessionStore.ts`, `frontend/src/stores/annotationStore.ts`, and `frontend/src/stores/uiStore.ts`.
- `framer-motion` 12.40.0 - UI animation in wizard/export components such as `frontend/src/components/wizard/WizardShell.tsx` and `frontend/src/components/export/ExportDialog.tsx`.
- `lucide-react` 1.17.0 - Icon components in `frontend/src/components/layout/` and `frontend/src/components/wizard/`.
- Radix UI packages - Dialog, scroll area, separator, slot, and tooltip primitives listed in `frontend/package.json`; active usage was not detected in `frontend/src/`.
- `class-variance-authority`, `clsx`, and `tailwind-merge` - Styling helpers; `clsx` and `tailwind-merge` are wrapped by `frontend/src/lib/utils.ts`.

## Configuration

**Environment:**
- Runtime configuration is file/path based, not environment-variable based. No `.env*` files, `os.environ`, `getenv`, `process.env`, or `import.meta.env` usage was detected.
- Backend constants live in `backend/config.py`, including `OUTPUTS_DIR`, `OUTPUT_DIR`, image/video extensions, `CONF_THRESHOLD`, ROI/detection toggles, and cache/display limits.
- User-selected dataset paths, output paths, YOLO weights, class names, and confidence threshold are sent to `POST /api/session/start` through `backend/api/session.py`.
- Startup wizard cache persists to `~/.inolabel/startup_cache.json` from `backend/core/startup_cache.py`.

**Build:**
- Frontend build: `frontend/package.json` script `build` runs `tsc -b && vite build`.
- Frontend dev server: `frontend/package.json` script `dev` runs Vite. `frontend/vite.config.ts` proxies `/api` to `http://127.0.0.1:7432` and `/ws` to `ws://127.0.0.1:7432`.
- Frontend TypeScript: `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, and `frontend/tsconfig.node.json`.
- Frontend lint: `frontend/eslint.config.js`.
- Backend dev server: `python build.py --dev` runs `python -m uvicorn backend.main:app --host 127.0.0.1 --port 7432 --reload --reload-dir backend` from `build.py`.
- Desktop build: `python build.py` builds the frontend, then runs PyInstaller with `InoLabel.spec`.
- Static frontend serving: `backend/main.py` mounts `frontend/dist` when present or bundled under `sys._MEIPASS`.

## Platform Requirements

**Development:**
- Python 3.9+ with dependencies from `requirements.txt`.
- Native Tkinter is required for wizard file/folder dialogs in `backend/api/wizard.py`; `README.md` notes `python3-tk` for Ubuntu/Debian.
- Native build toolchain is recommended by `README.md` for computer-vision dependencies.
- Optional CUDA can accelerate Ultralytics YOLO inference, per `README.md`.
- Node.js and npm are required for `frontend/package.json` scripts.
- Run backend on `127.0.0.1:7432` and frontend dev server on `localhost:5173`; these ports are hardcoded in `main.py`, `build.py`, `backend/main.py`, and `frontend/vite.config.ts`.

**Production:**
- Primary production target is a local Windows-style desktop bundle produced by PyInstaller from `InoLabel.spec`, with `frontend/dist` and `assets/` packaged as data files.
- The app is local-first and serves the React build from FastAPI in `backend/main.py`; no cloud hosting target or container deployment config was detected.
- User-generated datasets, model weights, outputs, and local cache are intentionally kept outside version control by `.gitignore`.

---

*Stack analysis: 2026-05-29*
