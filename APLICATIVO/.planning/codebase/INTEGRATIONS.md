---
last_mapped_commit: af6f39f6d52b32e68a7d38ed4a1b747fd1283f01
---

# External Integrations

**Analysis Date:** 2026-06-02

## APIs & External Services

**Local Backend API:**
- FastAPI service - Serves the React/Tauri frontend through local HTTP endpoints.
  - SDK/Client: Browser `fetch` wrapper in `frontend/src/api/client.ts`.
  - Auth: Not detected.
  - Server: `api_server.py` runs `app.api.main:app` on `127.0.0.1:8765`.
  - Routes: `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/classes.py`, and `app/api/routes/annotations.py`.
  - Frontend proxy: `frontend/vite.config.ts` proxies `/api` to `http://127.0.0.1:8765` and strips the `/api` prefix.
  - CORS: `app/api/main.py` allows `http://localhost:5173`, `tauri://localhost`, and `https://tauri.localhost`.

**Desktop Sidecar:**
- Tauri shell sidecar - Starts the Python API server process for the desktop frontend.
  - SDK/Client: `@tauri-apps/plugin-shell` and Rust `ShellExt` in `frontend/src-tauri/src/lib.rs`.
  - Auth: Not detected.
  - Sidecar name: `api_server` in `frontend/src-tauri/src/lib.rs`.
  - Sidecar support: enabled by `frontend/src-tauri/tauri.conf.json`.

**Machine Learning Runtime:**
- Ultralytics YOLO - Loads local `.pt` model weights selected by the user or expected as `model.pt`.
  - SDK/Client: `ultralytics.YOLO` from `requirements.txt`.
  - Auth: Not detected.
  - Model selection: startup wizard validates weights in `app/ui/startup/wizard.py`.
  - Runtime loading: `app/annotation/state/core_init.py` loads one or more models from `AnnotationSessionConfig.weights_paths`.
  - Detection use: `app/annotation/detection/frame_model_helpers.py` and `app/annotation_obb/detection/frame_model_helpers.py`.
  - External network use: Not detected in repo code; models are local files.

**Third-Party Cloud APIs:**
- Not detected. Source scan found no Stripe, Supabase, Firebase, AWS, GCP, Azure, OpenAI, Anthropic, Redis, database client, `requests`, `httpx`, or `aiohttp` integration in application code.

## Data Storage

**Databases:**
- Not detected.
  - Connection: Not applicable.
  - Client: Not applicable.

**File Storage:**
- Local filesystem only.
  - Input datasets: paths chosen by the user and discovered by `app/sources/discovery.py`.
  - Default paths: `DATA_ROOT`, `WEIGHTS_PATH`, `OUTPUT_DATASET_PREFIX`, and `SAVED_STATES_SUBDIR` in `app/config.py`.
  - Detection and tracking state: COCO JSON files named `annotations.coco.json`, `annotations_obb.coco.json`, and `__annotations.coco.json` handled by `app/core/output_state.py`.
  - Annotation persistence: image files and COCO JSON are written by `app/annotation/infrastructure/persistence/coco_storage.py` and `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`.
  - YOLO exports: images, labels, and `data.yaml` are written by `app/annotation/infrastructure/export/yolo_exporter.py` and `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py`.
  - COCO exports: JSON plus optional copied images are written by `app/annotation/infrastructure/export/coco_exporter.py`.
  - Classification state: `classification_state.json` and class folders are managed by `app/classification/dataset.py`.
  - Local user preferences: `.local/startup_cache.json` is written by `app/core/startup_cache.py`; `.local/keybinds.json` is written by `app/annotation/keybinds/keybind_repository.py`.
  - Ignored local data: `.gitignore` excludes `outputs/`, `dataset/`, `data/`, `models/`, `videos/`, `imagens/`, `dataset_original/`, and `.local/`.

**Caching:**
- Local JSON cache only.
  - Startup selections: `app/core/startup_cache.py`.
  - Keybinding profiles: `app/annotation/keybinds/keybind_repository.py`.
  - API runtime state: in-memory `runtime` object in `app/api/state.py`, frame globals in `app/api/routes/frames.py`, and annotation store globals in `app/api/routes/annotations.py`.
  - External cache service: Not detected.

## Authentication & Identity

**Auth Provider:**
- Not detected.
  - Implementation: Local desktop and local HTTP API run without authentication in `app/api/main.py` and `frontend/src/api/client.ts`.
  - Authorization headers, bearer token handling, session cookies, OAuth clients, and user identity models are not detected.

## Monitoring & Observability

**Error Tracking:**
- None detected.

**Logs:**
- Uvicorn logs local backend activity with `log_level="info"` in `api_server.py`.
- The classic desktop runner prints fatal errors to stderr in `app/runner.py`.
- UI modules use local dialogs and status messages for user-facing errors, including `app/ui/startup/wizard.py`.
- No Sentry, OpenTelemetry, hosted logging, metrics, or tracing integration is detected.

## CI/CD & Deployment

**Hosting:**
- No hosted web deployment is detected.
- Desktop distribution is local packaging via PyInstaller in `build.sh` and Tauri packaging via `frontend/src-tauri/tauri.conf.json`.

**CI Pipeline:**
- GitHub Actions - `.github/workflows/ci.yml`.
  - Python job installs `requirements.txt` and runs `python -m pytest -q || true`.
  - Node job uses Node.js 18 and runs Playwright demo tests from `.impeccable/demo/`.
  - Deployment/publishing steps are not detected.

## Environment Configuration

**Required env vars:**
- Not detected for the Python application.
- `TAURI_ENV_DEBUG` optionally changes Vite minification and sourcemaps in `frontend/vite.config.ts`.
- `VITE_` and `TAURI_ENV_*` are the only frontend env prefixes exposed by `frontend/vite.config.ts`.

**Secrets location:**
- Not applicable; no secret-bearing config files or required credentials are detected.
- `.env` files are not present in the repository root.
- Local runtime data and preferences belong in ignored paths such as `.local/`, `dataset/`, `models/`, and `outputs/` per `.gitignore`.

## Webhooks & Callbacks

**Incoming:**
- None detected.
- Local HTTP endpoints are application API routes only: `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/classes.py`, and `app/api/routes/annotations.py`.

**Outgoing:**
- None detected.
- Application code does not include outbound webhook dispatch, remote REST clients, or hosted callback URLs.

---

*Integration audit: 2026-06-02*
