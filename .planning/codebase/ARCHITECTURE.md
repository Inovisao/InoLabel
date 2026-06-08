<!-- refreshed: 2026-06-08 -->
# Architecture

**Analysis Date:** 2026-06-08

## System Overview

```text
+-------------------------------------------------------------+
|                        User Interfaces                       |
+-----------------------+-------------------+-----------------+
| React WebUI           | Tauri desktop     | Browser launcher|
| `frontend/src`        | `frontend/src-tauri` | `main.py`    |
+-----------+-----------+---------+---------+--------+--------+
            |                     |                  |
            v                     v                  v
+-------------------------------------------------------------+
| FastAPI application                                      |
| `app/api/main.py`, `app/api/routes/*`                    |
+-------------------------------------------------------------+
            |
            v
+-------------------------------------------------------------+
| In-process runtime state and schemas                     |
| `app/api/state.py`, `app/api/schemas.py`                 |
+-------------------------------------------------------------+
            |
            v
+-------------------------+-------------------+---------------+
| Core services           | Export services   | Tracking      |
| `app/core/*`            | `app/annotation/*`| `tracker/*`  |
| `app/sources/*`         | `app/annotation_obb/*`           |
+-------------------------------------------------------------+
            |
            v
+-------------------------------------------------------------+
| Local filesystem outputs and datasets                     |
| `outputs/`, `output/`, `saved_data_states/`, user paths   |
+-------------------------------------------------------------+
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Backend launcher | Starts uvicorn on `127.0.0.1:8765`, optionally opens a browser, and switches reload behavior with `INOLABEL_ENV`. | `main.py:44`, `api_server.py:16` |
| FastAPI app composition | Defines the API app, CORS origins, route registration, health check, and optional static frontend mount. | `app/api/main.py:14`, `app/api/main.py:30`, `app/api/main.py:53` |
| API schemas | Defines Pydantic request/response contracts for modes, sessions, frames, annotations, classes, keybinds, and export progress. | `app/api/schemas.py` |
| API runtime state | Owns process-local sessions, exports, frame paths, frame dimensions, annotation store, and annotation id counter. | `app/api/state.py:14`, `app/api/state.py:50`, `app/api/state.py:76` |
| Session routes | Validates input paths/models, replaces an active session safely, initializes output metadata, and exposes lifecycle/status actions. | `app/api/routes/session.py:38` |
| Frame routes | Discovers image frames for the active session, encodes frames to base64 JPEG, stores frame dimensions, and supports navigation. | `app/api/routes/frames.py:82`, `app/api/routes/frames.py:92` |
| Annotation routes | Reads/writes frame annotations, autosaves YOLO `.txt` labels, and loads resume labels from disk. | `app/api/routes/annotations.py:24`, `app/api/routes/annotations.py:135` |
| Export routes | Creates background export jobs, stages annotated frames, and calls YOLO export services. | `app/api/routes/export.py:25`, `app/api/routes/export.py:158` |
| React API client | Centralizes frontend HTTP calls under `/api` and normalizes backend error responses to thrown `Error`s. | `frontend/src/api/client.ts:1` |
| React session store | Starts/stops/recovers server sessions and initializes frames after successful session creation. | `frontend/src/stores/session.ts:19` |
| React annotation store | Fetches frames/classes, navigates frames, adds/removes annotations, and mirrors successful mutations into UI state. | `frontend/src/stores/annotation.ts:21` |
| React shell | Switches between wizard/project/history/help/shortcuts views and the active annotation workspace. | `frontend/src/App.tsx:24` |
| Annotation canvas | Renders server-provided images with Konva and converts drawn screen rectangles into image-space bboxes. | `frontend/src/components/canvas/AnnotationCanvas.tsx:14` |
| Export primitives | Represents export job state and validates split ratios. | `app/core/exporter.py:15`, `app/core/exporter.py:31` |
| Source discovery | Summarizes supported videos, images, folders, and image-list inputs independent of UI code. | `app/sources/discovery.py:28`, `app/sources/discovery.py:38` |
| Dataset export facade | Re-exports COCO/YOLO export helpers for scripts and compatibility callers. | `app/dataset_export.py` |
| Detection export implementation | Writes YOLO datasets with optional splits and no-split output. | `app/annotation/infrastructure/export/yolo_exporter.py:76`, `app/annotation/infrastructure/export/yolo_exporter.py:181` |
| OBB export implementation | Writes oriented bounding-box YOLO datasets. | `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py:43` |
| Tracking engine | Provides BYTETracker implementation and app-level multiclass wrapper. | `tracker/byte_tracker.py:145`, `app/tracking/multiclass_byte_tracking.py` |
| Legacy Tkinter mixins | Keeps desktop annotation, OBB, ROI, persistence, keybind, and classification logic split into mixins. | `app/annotation/shared.py`, `app/annotation/detection/__init__.py`, `app/annotation_obb/shared.py`, `app/classification/tools/*` |

## Pattern Overview

**Overall:** Local-first single-process WebUI with a FastAPI backend, React/Zustand client state, file-based persistence, and legacy Tkinter annotation modules.

**Key Characteristics:**
- Use `app/api/main.py` as the composition root for web routes; register new HTTP surfaces through `app/api/routes/*`.
- Keep backend request/response shapes in `app/api/schemas.py`; mirror frontend shapes in `frontend/src/api/types.ts`.
- Treat `app/api/state.py` as process-local state, not durable storage. Persist user-facing annotation work through label files and exports in output directories.
- Use `frontend/src/stores/session.ts` and `frontend/src/stores/annotation.ts` as the client-side state boundary instead of issuing ad hoc `fetch` calls in components.
- Keep import-time API dependencies free of Tkinter/UI modules; `tests/test_api_contract.py` asserts that `app.api.main` does not import `tkinter` or `app.ui`.

## Layers

**Launch Layer:**
- Purpose: Start the backend server and optionally open the browser.
- Location: `main.py`, `api_server.py`
- Contains: Uvicorn bootstrapping, PyInstaller stdout/stderr guards, development reload switch, browser opener.
- Depends on: `uvicorn`, `app.api.main`
- Used by: Local executable flow, development server invocation, packaged app entry points.

**FastAPI Route Layer:**
- Purpose: Expose HTTP endpoints for session setup, validation, frame navigation, annotation mutation, classes, keybinds, file browsing, and export jobs.
- Location: `app/api/main.py`, `app/api/routes/*`
- Contains: `APIRouter` modules with thin orchestration around schemas, process state, filesystem I/O, and export services.
- Depends on: `app/api/schemas.py`, `app/api/state.py`, `app/config.py`, `app/annotation/infrastructure/export/*`
- Used by: `frontend/src/api/client.ts`, FastAPI tests in `tests/test_api_contract.py`.

**Runtime State Layer:**
- Purpose: Hold active session state while uvicorn is running.
- Location: `app/api/state.py`
- Contains: `SessionState`, `_sessions`, `_exports`, `frame_paths`, `frame_dims`, `annotation_store`, and `next_ann_id`.
- Depends on: `app/core/exporter.py`
- Used by: `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `app/api/routes/export.py`, `app/api/routes/classes.py`.

**Core Domain Layer:**
- Purpose: Provide reusable configuration and pure service primitives independent from HTTP and React.
- Location: `app/core/*`, `app/sources/*`, `app/models.py`, `app/geometry.py`, `app/tracking/*`
- Contains: Session mode/config dataclasses, export job metadata, split validation, source discovery, palette, startup/output state helpers, geometry, tracking wrappers.
- Depends on: `app/config.py`, `tracker/*`, OpenCV/NumPy where needed.
- Used by: API routes, export services, Tkinter mixins, tests.

**Export/Persistence Layer:**
- Purpose: Convert in-memory annotation payloads and source images into YOLO/COCO dataset layouts.
- Location: `app/annotation/infrastructure/export/*`, `app/annotation_obb/infrastructure/export/*`, `app/annotation/infrastructure/persistence/*`, `app/dataset_export.py`
- Contains: YOLO split/no-split export, COCO export helpers, OBB YOLO export, compatibility facade.
- Depends on: `app/annotation/core/export/*`, `app/annotation/core/augmentation/*`, OpenCV, filesystem paths.
- Used by: `app/api/routes/export.py`, CLI utilities in `utils/*`, tests in `tests/test_dataset_export.py`, `tests/test_yolo_obb_export.py`.

**React UI Layer:**
- Purpose: Render the web annotation workflow and manage client interaction state.
- Location: `frontend/src/*`
- Contains: `App.tsx`, pages, layout components, wizard components, modal components, Konva canvas, Zustand stores, API client, CSS.
- Depends on: React, Zustand, Konva, Radix UI, lucide icons, `/api` backend.
- Used by: Vite dev server, FastAPI static mount when `frontend/dist` exists, Tauri shell.

**Tauri Shell Layer:**
- Purpose: Package the Vite frontend in a desktop shell.
- Location: `frontend/src-tauri/*`
- Contains: Tauri config, Rust `run()` builder, app entry point.
- Depends on: Built frontend assets in `frontend/dist`, Tauri plugins.
- Used by: `npm run tauri` and Tauri bundling.

**Legacy Tkinter Layer:**
- Purpose: Preserve desktop annotation flows and classification helper behavior separate from the WebUI API.
- Location: `app/annotation/*`, `app/annotation_obb/*`, `app/classification/*`, `utils/annotation_tool_bytetracked.py`
- Contains: Shared Tkinter/OpenCV/YOLO imports, annotation mixins, OBB mixins, classification dataset actions, legacy monolithic annotation tool.
- Depends on: Tkinter, PIL, OpenCV, Ultralytics, tracker package, `app.config`.
- Used by: Legacy tests and compatibility import paths; not imported by `app/api/main.py`.

## Data Flow

### Web Session Start Path

1. `frontend/src/components/wizard/Wizard.tsx` collects mode, data path, output path, model path, classes, confidence, and resume settings.
2. `frontend/src/stores/session.ts:19` posts the request through `frontend/src/api/client.ts:1` to `/api/session/start`.
3. `app/api/routes/session.py:38` validates paths/model, stops any active session through `app/api/state.py`, creates output metadata, counts frames via `run_in_threadpool`, and creates `SessionState`.
4. `frontend/src/stores/session.ts:19` calls `/api/frames/init` after start; `app/api/routes/frames.py:82` populates `app/api/state.py` `frame_paths`.
5. `frontend/src/App.tsx:24` switches from the wizard to `frontend/src/pages/AnnotatePage.tsx`.

### Frame Display And Annotation Path

1. `frontend/src/pages/AnnotatePage.tsx` calls `fetchClasses()` and `fetchFrame()` from `frontend/src/stores/annotation.ts:21`.
2. `app/api/routes/classes.py` reads active session classes from `app/api/state.py`; `app/api/routes/frames.py:92` returns the current frame as base64 JPEG with current annotations.
3. `frontend/src/components/canvas/AnnotationCanvas.tsx:14` decodes `FrameResponse.image_b64`, scales it to the canvas, and converts drawn rectangles into image pixel coordinates.
4. `frontend/src/stores/annotation.ts:21` posts bboxes to `/api/annotations/{image_id}`.
5. `app/api/routes/annotations.py:135` creates an `Annotation`, stores it in `app/api/state.py`, and calls `_autosave`.
6. `app/api/routes/annotations.py:24` writes YOLO label files into `<output_path>/labels/<frame>.txt`.

### Export Path

1. `frontend/src/components/modals/ExportModal.tsx:30` posts export settings to `/api/export`.
2. `app/api/routes/export.py:158` validates the session, split ratios, and destination path, then creates an `ExportJob` from `app/core/exporter.py:15`.
3. `app/api/routes/export.py:25` runs as a FastAPI background task, reads `app/api/state.py` frame/annotation stores, stages source images in a temporary directory, and calls `export_yolo_dataset` or `export_yolo_no_split`.
4. `app/annotation/infrastructure/export/yolo_exporter.py:76` or `app/annotation/infrastructure/export/yolo_exporter.py:181` writes the dataset output.
5. `frontend/src/components/modals/ExportModal.tsx:30` polls `/api/export/{export_id}/progress` until `ExportJob.status` becomes `done` or `error`.

### Legacy Tkinter Annotation Path

1. `utils/annotation_tool_bytetracked.py:1192` is a standalone Tkinter entry point for the legacy tracked annotation tool.
2. `app/annotation/__init__.py:4` lazily resolves `AnnotationTool` from `app.annotation.tool`; the source file is not present as `.py` in this checkout.
3. Mixins under `app/annotation/detection/*`, `app/annotation/state/*`, `app/annotation/sources/*`, and `app/annotation/roi/*` compose detection, state, source, ROI, and persistence behavior.
4. OBB-specific behavior extends shared annotation behavior from `app/annotation_obb/shared.py` and `app/annotation_obb/*`.

**State Management:**
- Backend state is process-local dictionaries and lists in `app/api/state.py`. It is reset by `reset_state()` and by session stop/start flows.
- Frontend state is split between `frontend/src/stores/session.ts` for lifecycle state and `frontend/src/stores/annotation.ts` for frame/class/annotation state.
- Durable annotation persistence is filesystem-based: `.inolabel.json` project metadata from `app/api/routes/session.py`, YOLO label autosaves from `app/api/routes/annotations.py`, and export outputs from `app/api/routes/export.py`.

## Key Abstractions

**Session Contracts:**
- Purpose: Represent supported modes and validated session configuration.
- Examples: `app/core/session.py:13`, `app/core/session.py:33`, `app/api/schemas.py`
- Pattern: Enum/dataclass domain model plus Pydantic HTTP schema.

**Process Runtime State:**
- Purpose: Keep the single active API process aware of sessions, frame list, image dimensions, and annotations.
- Examples: `app/api/state.py:14`, `app/api/state.py:50`, `app/api/state.py:76`
- Pattern: Module-level registries with small helper functions.

**Route Modules:**
- Purpose: Keep each HTTP concern in its own `APIRouter` module.
- Examples: `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `app/api/routes/export.py`
- Pattern: Route-level orchestration over shared state and domain/export helpers.

**Zustand Stores:**
- Purpose: Keep React components thin and put server synchronization in focused stores.
- Examples: `frontend/src/stores/session.ts:19`, `frontend/src/stores/annotation.ts:21`
- Pattern: Store action methods wrap API calls and update local state after success.

**Export Jobs:**
- Purpose: Track background export progress and output destination.
- Examples: `app/core/exporter.py:15`, `app/api/routes/export.py:158`
- Pattern: Mutable dataclass stored in `app/api/state.py` export registry.

**Dataset Export Services:**
- Purpose: Convert COCO-like payloads and staged images into training dataset layouts.
- Examples: `app/annotation/infrastructure/export/yolo_exporter.py:76`, `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py:43`
- Pattern: Pure-ish functions parameterized by payload, source directory, output root, split ratios, and optional progress callbacks.

**Legacy Mixin Modules:**
- Purpose: Split Tkinter annotation tool behavior into feature-specific mixins.
- Examples: `app/annotation/detection/__init__.py`, `app/annotation/state/__init__.py`, `app/annotation/roi/__init__.py`
- Pattern: Multiple inheritance mixins sharing a large dependency surface through `app/annotation/shared.py`.

## Entry Points

**Packaged/local web app launcher:**
- Location: `main.py`
- Triggers: `python main.py`, packaged executable entry point.
- Responsibilities: Start uvicorn, wait for `/health`, open the browser, handle PyInstaller stdout/stderr guards.

**Backend-only API launcher:**
- Location: `api_server.py`
- Triggers: `python api_server.py`.
- Responsibilities: Start uvicorn without browser-opening behavior.

**FastAPI ASGI app:**
- Location: `app/api/main.py`
- Triggers: Uvicorn imports `app.api.main:app`; tests import the app via `TestClient`.
- Responsibilities: Compose middleware, routers, health check, and static frontend serving.

**React frontend:**
- Location: `frontend/src/main.tsx`, `frontend/src/App.tsx`
- Triggers: Vite dev server, built frontend loaded through FastAPI static mount, or Tauri shell.
- Responsibilities: Render the UI shell and switch between wizard, project/history/help views, and active annotation workspace.

**Tauri desktop shell:**
- Location: `frontend/src-tauri/src/main.rs`, `frontend/src-tauri/src/lib.rs`
- Triggers: `npm run tauri`, Tauri bundler.
- Responsibilities: Create the native desktop window for the frontend.

**CLI utilities:**
- Location: `utils/merge_yolo_splits.py`, `utils/convert_coco_tracking_to_detection.py`, `utils/convert_coco_to_yolo_dataset.py`, `utils/augment_output_dataset.py`, `utils/annotation_tool_bytetracked.py`
- Triggers: Direct Python execution.
- Responsibilities: Dataset conversion/augmentation and legacy tracked annotation.

## Architectural Constraints

- **Threading:** Uvicorn handles async HTTP traffic; blocking filesystem/frame counting uses `run_in_threadpool` in `app/api/routes/session.py`, and Tkinter browse dialogs use `run_in_threadpool` in `app/api/routes/browse.py`.
- **Background work:** Export jobs run through FastAPI `BackgroundTasks` in `app/api/routes/export.py` and mutate `ExportJob` instances stored in `app/api/state.py`.
- **Global state:** API process state is module-level and mutable in `app/api/state.py`. Frame navigation also has module globals `_current_index` and `_loaded_from_disk` in `app/api/routes/frames.py`.
- **Durability:** Sessions do not survive backend process restart except through output files and project metadata under output paths.
- **Filesystem trust boundary:** User-supplied paths are resolved in route handlers such as `app/api/routes/session.py` and `app/api/routes/export.py`; export dataset names are constrained by `_safe_output_path` in `app/api/routes/export.py`.
- **UI import boundary:** Keep `app/api/main.py` and imported API modules free of Tkinter and `app.ui` imports; `tests/test_api_contract.py` asserts this boundary.
- **Circular imports:** `app/api/routes/frames.py` imports `_load_frame_from_txt` from `app/api/routes/annotations.py` inside `_lazy_load_from_disk` to avoid a top-level cycle. Preserve that lazy import unless the state contract is redesigned.
- **Generated artifacts:** `build/`, `dist/`, `frontend/dist/`, `frontend/src-tauri/target/`, `output/`, `outputs/`, and `saved_data_states/` are output/generated paths per `.gitignore`.

## Anti-Patterns

### Importing Desktop UI From API Modules

**What happens:** API tests explicitly guard against importing `tkinter` or `app.ui` when `app/api/main.py` loads.
**Why it's wrong:** It couples headless HTTP tests and WebUI startup to desktop-only dependencies and can break server import on non-desktop environments.
**Do this instead:** Keep desktop file pickers lazily imported inside route functions as in `app/api/routes/browse.py`; keep shared API logic in `app/core/*`, `app/sources/*`, or `app/api/*`.

### Bypassing Frontend Stores For Server State

**What happens:** Components can technically call `frontend/src/api/client.ts` directly.
**Why it's wrong:** Session and annotation state then drift away from `frontend/src/stores/session.ts` and `frontend/src/stores/annotation.ts`, which own active session, frame, class, and annotation state.
**Do this instead:** Add new lifecycle actions to `frontend/src/stores/session.ts` and new frame/annotation actions to `frontend/src/stores/annotation.ts`, then call those actions from components.

### Writing Export Logic In Routes

**What happens:** `app/api/routes/export.py` stages payloads and invokes export helpers while tracking job progress.
**Why it's wrong:** Route modules should orchestrate HTTP behavior; dataset layout decisions belong in export services for reuse by API and CLI utilities.
**Do this instead:** Put reusable dataset layout logic in `app/annotation/infrastructure/export/*` or `app/annotation_obb/infrastructure/export/*`, expose compatibility imports through `app/dataset_export.py`, and keep routes focused on validation, job creation, and state updates.

### Adding New State Registries Outside `app/api/state.py`

**What happens:** Route-level globals exist in `app/api/routes/frames.py` for current frame and loaded-from-disk tracking.
**Why it's wrong:** Additional route-local state makes resets and tests less predictable because `app/api/state.py:76` is the main reset point.
**Do this instead:** Prefer state fields/helpers in `app/api/state.py`; update `reset_state()` when new process-local API state is required.

## Error Handling

**Strategy:** Validate inputs at route boundaries, raise `HTTPException` for client-visible API errors, log non-critical persistence failures, and surface frontend HTTP failures as thrown `Error`s.

**Patterns:**
- Use `HTTPException(status_code=422)` for invalid user inputs in `app/api/routes/session.py`, `app/api/routes/validation.py`, and `app/api/routes/export.py`.
- Use `HTTPException(status_code=404)` for missing sessions, frames, annotations, and exports in `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, and `app/api/routes/export.py`.
- Use route-local logging for non-fatal autosave/load failures in `app/api/routes/annotations.py`.
- Use `frontend/src/api/client.ts` to parse backend error JSON and throw `Error` to stores/components.

## Cross-Cutting Concerns

**Logging:** Backend route modules use Python `logging` in `app/api/routes/session.py` and `app/api/routes/annotations.py`; uvicorn logging is configured from `main.py` and `api_server.py` via `log_level` and `log_config=None`.

**Validation:** HTTP validation is split between Pydantic validators in `app/api/schemas.py`, explicit filesystem checks in `app/api/routes/session.py`, and path/model/project validation routes in `app/api/routes/validation.py`.

**Authentication:** Not detected. FastAPI routes in `app/api/main.py` are local-only by default because launchers bind uvicorn to `127.0.0.1`.

**Configuration:** Runtime paths and defaults live in `app/config.py`, including `OUTPUT_BASE`, `ASSETS_DIR`, `LOCAL_DIR`, file extensions, confidence threshold, and PyInstaller path handling.

**Testing Boundary:** API tests in `tests/test_api_contract.py` assert import boundaries, modes, validation, session lifecycle, export lifecycle, and keybind persistence around the web API.

---

*Architecture analysis: 2026-06-08*
