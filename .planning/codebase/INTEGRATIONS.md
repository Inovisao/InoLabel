# External Integrations

**Analysis Date:** 2026-06-08

## APIs & External Services

**Local Application API:**
- FastAPI service - The WebUI talks to an in-process/local backend under `/api`, and the backend also exposes `/health`.
  - SDK/Client: Browser `fetch` wrapper in `frontend/src/api/client.ts`; FastAPI routers in `app/api/main.py` and `app/api/routes/*.py`.
  - Auth: Not detected.
  - Runtime endpoint: `http://127.0.0.1:8765` from `main.py` and `api_server.py`; Vite proxy target in `frontend/vite.config.ts`.
  - Development endpoint: `http://localhost:5173` from `frontend/vite.config.ts` and `frontend/src-tauri/tauri.conf.json`.

**Computer Vision Model Runtime:**
- Ultralytics YOLO - Optional local `.pt` model loading for detection-assisted annotation.
  - SDK/Client: `ultralytics.YOLO` from `requirements.txt`, used lazily in `app/core/detector.py` and directly in `app/annotation/state/core_init.py`.
  - Auth: Not detected.
  - Model path: `model.pt` next to the executable by default via `app/config.py`; user-selected `.pt` validated by `app/api/routes/session.py` and `app/api/routes/validation.py`.

**Native Desktop Shell:**
- Tauri sidecar process - Tauri launches the Python `api_server` sidecar and displays the frontend bundle.
  - SDK/Client: `tauri-plugin-shell` in `frontend/src-tauri/Cargo.toml`; sidecar spawn in `frontend/src-tauri/src/lib.rs`.
  - Auth: Not detected.

**Native File Picker:**
- Tkinter file/folder dialogs - Local desktop picker endpoints for selecting datasets and model files.
  - SDK/Client: Python standard library `tkinter` in `app/api/routes/browse.py`.
  - Auth: Not detected.

**Package Registries / Build-Time Services:**
- PyPI - Python dependencies installed from `requirements.txt` by `README.md`, `build.sh`, `build.ps1`, and `.github/workflows/ci.yml`.
  - SDK/Client: `pip`.
  - Auth: Not detected.
- npm registry - Frontend dependencies resolved by npm from `frontend/package.json` and `frontend/package-lock.json`.
  - SDK/Client: `npm`.
  - Auth: Not detected.
- GitHub Actions - CI runs on push/pull_request to `main` and `master`.
  - SDK/Client: `.github/workflows/ci.yml`.
  - Auth: Repository-provided GitHub Actions token only; no explicit secrets referenced in workflow.

## Data Storage

**Databases:**
- Not detected.
  - Connection: Not applicable.
  - Client: Not applicable.

**File Storage:**
- Local filesystem only.
  - Input datasets: User-selected folders, images, videos, or list files validated in `app/api/routes/session.py` and `app/api/routes/validation.py`.
  - Model files: Local `.pt` paths validated in `app/api/routes/session.py` and `app/api/routes/validation.py`.
  - Output projects: Default output root from `OUTPUT_BASE` in `app/config.py`; project metadata written to `.inolabel.json` in `app/api/routes/session.py`.
  - Annotation labels and exports: YOLO/COCO files and copied images written by `app/annotation/infrastructure/export/yolo_exporter.py`, `app/annotation/infrastructure/export/coco_exporter.py`, `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py`, and `app/api/routes/export.py`.
  - Keybind state: JSON stored under `LOCAL_DIR` through `app/api/routes/keybinds.py` and `app/annotation/keybinds/keybind_repository.py`.
  - Startup/output state: JSON state files handled by `app/core/startup_cache.py`, `app/core/output_state.py`, and `app/classification/dataset.py`.

**Caching:**
- In-process FastAPI state only.
  - Sessions and export jobs: Module-level dictionaries in `app/api/state.py`.
  - Frame paths, dimensions, and annotations: Module-level stores in `app/api/state.py`, read/write by `app/api/routes/frames.py` and `app/api/routes/annotations.py`.
  - Startup cache: Local JSON cache in `app/core/startup_cache.py`.

## Authentication & Identity

**Auth Provider:**
- Not detected.
  - Implementation: No route dependencies, login endpoints, token verification, authorization headers, or frontend identity flow detected in `app/api/`, `frontend/src/`, `main.py`, or `api_server.py`.
  - Note: `python-jose[cryptography]` appears in `requirements.txt` and `jose` appears in `InoLabel.spec` hidden imports, but no source-level JWT/auth implementation was detected.

## Monitoring & Observability

**Error Tracking:**
- None detected.

**Logs:**
- Python standard logging for backend events. Evidence: `app/api/routes/session.py`.
- Uvicorn logging level is `debug` when `INOLABEL_ENV=development`, otherwise `info`, with `log_config=None`. Evidence: `main.py`, `api_server.py`.
- Build scripts write console status and failure messages. Evidence: `build.sh`, `build.ps1`.

## CI/CD & Deployment

**Hosting:**
- Local desktop/browser deployment.
  - FastAPI binds `127.0.0.1:8765` in `main.py` and `api_server.py`.
  - FastAPI serves built frontend assets from `frontend/dist` when present in `app/api/main.py`.
  - PyInstaller bundles `assets` and `frontend/dist` through `InoLabel.spec`, `build.sh`, and `build.ps1`.
  - Tauri uses `frontend/dist` and an `api_server` sidecar through `frontend/src-tauri/tauri.conf.json` and `frontend/src-tauri/src/lib.rs`.

**CI Pipeline:**
- GitHub Actions.
  - Workflow: `.github/workflows/ci.yml`.
  - Triggers: push and pull_request to `main` and `master`.
  - Python job: setup Python 3.9, install `requirements.txt`, run `python -m pytest -q || true`.
  - Node job segment: setup Node 18 and run demo Playwright tests in `.impeccable/demo`.

## Environment Configuration

**Required env vars:**
- None required for normal local execution.

**Optional env vars:**
- `INOLABEL_ENV` - Set to `development` for Uvicorn reload/debug in `main.py` and `api_server.py`.
- `INOLABEL_OUTPUT_BASE` - Override output root in `app/config.py`.
- `INOLABEL_ASSETS_DIR` - Override asset directory in `app/config.py`.
- `INOLABEL_LOCAL_DIR` - Override local state directory in `app/config.py`.
- `CONF_THRESHOLD` - Override YOLO confidence threshold in `app/config.py`.
- `SAVE_RECTIFIED_FRAMES` - Enable rectified frame saving in `app/config.py`.
- `MANUAL_IOU_THRESHOLD` - Override manual/detection merge IoU threshold in `app/config.py`.
- `TAURI_ENV_DEBUG` - Controls frontend minification and sourcemap behavior in `frontend/vite.config.ts`.
- `VITE_*` - Allowed frontend environment prefix in `frontend/vite.config.ts`.

**Secrets location:**
- Not detected.
- `.env` files were not detected in the repository root scan.
- `.npmrc`, credential files, private keys, and secret directories were not read or required for this audit.

## Webhooks & Callbacks

**Incoming:**
- None detected.
  - No webhook-specific endpoints detected in `app/api/routes/*.py`.
  - Local API endpoints are user-interface endpoints, not external callbacks. Evidence: `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `app/api/routes/export.py`.

**Outgoing:**
- None detected.
  - No `requests` or `httpx` client usage detected in source.
  - `main.py` polls local `/health` through `urllib.request.urlopen` and opens the local browser URL through `webbrowser.open`; this is local process coordination, not an external service integration.

---

*Integration audit: 2026-06-08*
