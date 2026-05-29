# External Integrations

**Analysis Date:** 2026-05-29

## APIs & External Services

**Local HTTP API:**
- FastAPI app - Serves the frontend and local API on `127.0.0.1:7432`.
  - SDK/Client: `axios` wrapper in `frontend/src/lib/api.ts`.
  - Auth: None.
  - Server implementation: `backend/main.py`.
  - Routes: `/api/health` in `backend/main.py`, `/api/session/*` in `backend/api/session.py`, `/api/frame/*` in `backend/api/frame.py`, `/api/export` in `backend/api/export.py`, and `/api/wizard/*` in `backend/api/wizard.py`.
  - Development proxy: `/api` in `frontend/vite.config.ts` targets `http://127.0.0.1:7432`.

**Local WebSocket API:**
- Real-time frame/state channel - Pushes annotation state snapshots and receives simple action messages.
  - SDK/Client: browser `WebSocket` in `frontend/src/hooks/useWebSocket.ts`.
  - Auth: None.
  - Server implementation: `backend/api/ws.py`.
  - Endpoint: `/ws`.
  - Development proxy: `/ws` in `frontend/vite.config.ts` targets `ws://127.0.0.1:7432`.
  - Client URL behavior: `frontend/src/hooks/useWebSocket.ts` connects to `ws://{window.location.hostname}:7432/ws` on `localhost`, otherwise to the current page port.

**Computer Vision / ML Libraries:**
- Ultralytics YOLO - Optional local model inference from user-selected `.pt` files.
  - SDK/Client: `ultralytics.YOLO` in `backend/annotation/state/core_init.py`.
  - Auth: None.
  - Model source: local file paths passed in `weights_paths` to `backend/api/session.py`.
- OpenCV - Local image/video IO, rendering, ROI homography, augmentation, and dataset export.
  - SDK/Client: `cv2` imports across `backend/annotation/`, `backend/annotation_obb/`, `backend/annotation/core/augmentation/augmentation_service.py`, `backend/annotation/infrastructure/export/yolo_exporter.py`, and `backend/services/classification_service.py`.
  - Auth: None.
- BYTETracker - Local tracking implementation copied into `backend/tracker/` and `tracker/`, orchestrated by `backend/tracking/multiclass_byte_tracking.py`.
  - SDK/Client: in-repo Python modules, with SciPy/lapx assignment in `backend/tracker/matching.py`.
  - Auth: None.

**Native Desktop OS Integrations:**
- pywebview - Opens the local FastAPI UI in a desktop window from `main.py`.
  - SDK/Client: `webview`.
  - Auth: None.
- Tkinter file dialogs - Native folder/file picker endpoints in `backend/api/wizard.py`.
  - SDK/Client: `tkinter.filedialog`.
  - Auth: None.

**Cloud APIs:**
- Not detected. No Stripe, Supabase, Firebase, AWS, Azure, Google Cloud, OpenAI, Anthropic, Sentry, Redis, database, or outbound HTTP client integration was found in source scans.

## Data Storage

**Databases:**
- Not detected.
  - Connection: Not applicable.
  - Client: Not applicable.

**File Storage:**
- Local filesystem only.
  - User-selected input datasets are validated by `backend/api/wizard.py` and session-started by `backend/api/session.py`.
  - Default output root is `outputs/` via `OUTPUTS_DIR` in `backend/config.py`.
  - Annotation states are JSON files such as `annotations.coco.json`, `annotations_obb.coco.json`, and `__annotations.coco.json`, discovered by `backend/core/output_state.py`.
  - Exported YOLO datasets are written by `backend/annotation/infrastructure/export/yolo_exporter.py` and `backend/annotation_obb/infrastructure/export/yolo_obb_exporter.py`.
  - Classification state is stored in local JSON by `backend/classification/dataset.py`.
  - Startup wizard cache is stored at `~/.inolabel/startup_cache.json` by `backend/core/startup_cache.py`.
  - Packaged static assets are read from `assets/` and `frontend/dist` through `backend/config.py`, `backend/main.py`, and `InoLabel.spec`.

**Caching:**
- Local JSON startup cache in `~/.inolabel/startup_cache.json` from `backend/core/startup_cache.py`.
- In-memory active session singleton in `backend/services/session_manager.py`.
- No Redis, Memcached, browser persistence layer, or server-side cache service detected.

## Authentication & Identity

**Auth Provider:**
- None.
  - Implementation: Local desktop/local-network API has no login, token, session cookie, CSRF guard, or permission layer in `backend/main.py` or `backend/api/`.
  - CORS: `backend/main.py` allows `http://localhost:5173` and `http://127.0.0.1:5173` for development.

## Monitoring & Observability

**Error Tracking:**
- None detected.

**Logs:**
- Python standard logging is configured globally in `backend/main.py` with `logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")`.
- WebSocket connect/disconnect and action-processing warnings are logged in `backend/api/ws.py`.
- Build and dev scripts print status and errors to stdout/stderr from `build.py`.
- No structured log sink, telemetry exporter, metrics endpoint, tracing, or hosted monitoring integration detected.

## CI/CD & Deployment

**Hosting:**
- Local desktop deployment via PyInstaller using `build.py` and `InoLabel.spec`.
- Local development hosting via Uvicorn (`backend.main:app`) and Vite (`frontend/package.json`).
- No cloud hosting manifest detected (`Dockerfile`, Compose, Procfile, Vercel, Netlify, Fly, Railway, or GitHub Actions workflow not found).

**CI Pipeline:**
- None detected. No `.github/workflows/` files were found.

## Environment Configuration

**Required env vars:**
- None detected.

**Secrets location:**
- Not applicable. No `.env*` files were present and no secret/config credential files were inspected or required.
- User data and local generated artifacts are excluded by `.gitignore`, including `dataset/`, `models/`, `outputs/`, `.local/`, and `.inolabel/`.

## Webhooks & Callbacks

**Incoming:**
- FastAPI HTTP endpoints in `backend/api/` are local application endpoints, not third-party webhooks.
- WebSocket endpoint `/ws` in `backend/api/ws.py` accepts client action messages from the frontend.

**Outgoing:**
- No third-party outgoing webhooks detected.
- Internal callback broadcasting is implemented by `session_manager.add_frame_listener(_sync_broadcast)` in `backend/api/ws.py`, using in-process listeners from `backend/services/session_manager.py`.

---

*Integration audit: 2026-05-29*
