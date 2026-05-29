<!-- refreshed: 2026-05-29 -->
# Architecture

**Analysis Date:** 2026-05-29

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│               Desktop Shell + React Frontend                 │
├──────────────────┬──────────────────┬───────────────────────┤
│   pywebview app  │  Wizard screens  │   Annotation layout   │
│   `main.py`      │ `frontend/src/`  │   `frontend/src/`     │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         │ HTTP `/api/*`    │ WebSocket `/ws`     │ Static files
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  `backend/main.py`, `backend/api/*.py`                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 Session Runtime Singleton                    │
│        `backend/services/session_manager.py`                 │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│        Annotation, OBB, Classification Domain Services        │
│ `backend/annotation/`, `backend/annotation_obb/`,             │
│ `backend/services/classification_service.py`                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│        Filesystem Datasets, COCO State, YOLO Exports          │
│        `outputs/`, `backend/core/output_state.py`             │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Desktop launcher | Starts Uvicorn in a daemon thread, waits for `/api/health`, then opens pywebview against the local server. | `main.py` |
| FastAPI app | Creates the API application, registers routers, enables Vite dev CORS, and serves `frontend/dist` in packaged mode. | `backend/main.py` |
| Session API | Validates wizard input, builds immutable session config, starts/stops the active tool through the session singleton. | `backend/api/session.py` |
| Frame API | Applies annotation actions to the active tool and returns state snapshots with updated frame data. | `backend/api/frame.py` |
| Export API | Dispatches export work to classification or annotation tools. | `backend/api/export.py` |
| Wizard API | Lists modes, validates paths, persists startup cache, opens native file/folder dialogs, and reads output-state metadata. | `backend/api/wizard.py` |
| WebSocket API | Maintains active browser connections and broadcasts `SessionManager` state updates. | `backend/api/ws.py` |
| SessionManager | Owns the single active runtime tool and selects the concrete implementation by `AnnotationTaskMode`. | `backend/services/session_manager.py` |
| Standard annotation tool | Composes detection, ROI, persistence, export, lifecycle, state, source, tracking, and display mixins into a UI-free backend tool. | `backend/annotation/tool.py` |
| OBB annotation tool | Composes the OBB-specific runtime, geometry, workflow, persistence, export, and display mixins. | `backend/annotation_obb/tool.py` |
| Classification service | Implements image classification workflow, class-folder management, state persistence, undo, and export. | `backend/services/classification_service.py` |
| React app shell | Switches between setup wizard and annotation workspace by Zustand session state. | `frontend/src/App.tsx` |
| API client | Centralizes Axios calls to FastAPI under `/api`. | `frontend/src/lib/api.ts` |
| Realtime client | Connects to `/ws`, parses state messages, and writes them into the annotation store. | `frontend/src/hooks/useWebSocket.ts` |
| Frontend state stores | Hold wizard/session state, annotation state, and UI-only control state. | `frontend/src/stores/sessionStore.ts`, `frontend/src/stores/annotationStore.ts`, `frontend/src/stores/uiStore.ts` |

## Pattern Overview

**Overall:** Local desktop/web hybrid with a FastAPI backend, React frontend, singleton session runtime, and mixin-composed domain services.

**Key Characteristics:**
- Use `main.py` for installed desktop execution; use `build.py --dev` plus `frontend` Vite dev server for local development.
- Route all frontend backend access through `/api` REST endpoints and `/ws` state pushes.
- Keep exactly one active annotation/classification runtime per Python process through `session_manager` in `backend/services/session_manager.py`.
- Model annotation workflows as concrete tools selected from `AnnotationTaskMode` in `backend/core/session.py`.
- Persist user work to filesystem output directories under `outputs/` through COCO JSON, image folders, homography files, and YOLO dataset exports.

## Layers

**Desktop Entry Layer:**
- Purpose: Boot the local API server and present the app as a desktop window.
- Location: `main.py`
- Contains: Uvicorn thread startup, health polling, optional pywebview import, window creation.
- Depends on: `backend.main`, `uvicorn`, `webview`.
- Used by: End users running `python main.py` and PyInstaller output from `InoLabel.spec`.

**FastAPI Transport Layer:**
- Purpose: Expose session, wizard, frame, export, and realtime APIs.
- Location: `backend/main.py`, `backend/api/session.py`, `backend/api/frame.py`, `backend/api/export.py`, `backend/api/wizard.py`, `backend/api/ws.py`
- Contains: `APIRouter` modules, Pydantic request models, HTTP validation, WebSocket connection management.
- Depends on: `backend.services.session_manager`, `backend.core.session`, `backend.core.output_state`.
- Used by: `frontend/src/lib/api.ts`, `frontend/src/hooks/useWebSocket.ts`.

**Session Runtime Layer:**
- Purpose: Keep one active backend tool and normalize state access for REST/WebSocket callers.
- Location: `backend/services/session_manager.py`
- Contains: `SessionManager.start()`, `SessionManager.stop()`, `SessionManager.get_state()`, frame listener callbacks, tool factory.
- Depends on: `backend.annotation.tool.AnnotationTool`, `backend.annotation_obb.tool.OBBAnnotationTool`, `backend.services.classification_service.ClassificationService`.
- Used by: Every API router in `backend/api/`.

**Core Domain Layer:**
- Purpose: Define session modes, immutable session configuration, output-state discovery, startup cache, and reusable data models.
- Location: `backend/core/`, `backend/models.py`, `backend/config.py`
- Contains: `AnnotationTaskMode`, `AnnotationSessionConfig`, output directory creation, COCO state loading, `Detection`, tracker args, filesystem constants.
- Depends on: Standard library, `numpy` for detection model data.
- Used by: API routers, session manager, annotation tools, classification service, tests.

**Annotation Workflow Layer:**
- Purpose: Process frames, run YOLO, manage ROI/homography, tracking IDs, manual edits, review navigation, autosave, and export.
- Location: `backend/annotation/`
- Contains: Mixin modules grouped by `application`, `core`, `detection`, `infrastructure`, `roi`, `sources`, `state`, `ui`.
- Depends on: `backend.annotation.shared`, `backend.tracking`, `backend.tracker`, `backend.geometry`, `ultralytics`, `cv2`, `PIL`, `numpy`.
- Used by: `backend/annotation/tool.py`.

**OBB Workflow Layer:**
- Purpose: Provide oriented bounding box variants of annotation runtime state, geometry, frame pipeline, selection/editing, review, persistence, and YOLO OBB export.
- Location: `backend/annotation_obb/`
- Contains: OBB tool composition, OBB geometry helpers, OBB persistence/export modules, OBB display modules.
- Depends on: Shared annotation state/source mixins, OBB-specific geometry in `backend/annotation_obb/geometry/obb_geometry.py`.
- Used by: `SessionManager._build_tool()` for `AnnotationTaskMode.OBB`.

**Classification Workflow Layer:**
- Purpose: Discover images, copy images into class directories, persist classification state, support undo, and export classification datasets.
- Location: `backend/classification/`, `backend/services/classification_service.py`
- Contains: Dataset functions, classification records/state models, state mixin, service facade.
- Depends on: `backend.config`, `backend.core.session`.
- Used by: `SessionManager._build_tool()` for `AnnotationTaskMode.CLASSIFICATION`.

**Tracking Layer:**
- Purpose: Adapt BYTETracker for single-class and per-class object tracking.
- Location: `backend/tracker/`, `backend/tracking/multiclass_byte_tracking.py`, root `tracker/`
- Contains: ByteTrack-derived tracking classes, Kalman filter, matching helpers, multiclass wrapper.
- Depends on: `numpy`, `scipy`, `lapx`, `backend.models.ByteTrackerArgs`.
- Used by: Runtime state and source helpers in `backend/annotation/`.

**React UI Layer:**
- Purpose: Render setup wizard and annotation workspace, send user actions to FastAPI, and render frame images and SVG overlays.
- Location: `frontend/src/`
- Contains: App shell, components, hooks, Zustand stores, typed API client, shared TypeScript types.
- Depends on: React, Vite, Zustand, Axios, Framer Motion, Lucide, Tailwind CSS.
- Used by: Browser/webview clients and served static build from `backend/main.py`.

## Data Flow

### Desktop Startup Path

1. `main()` starts a daemon thread that imports `backend.main.app` and runs Uvicorn on `127.0.0.1:7432` (`main.py:14`, `main.py:32`).
2. `_wait_for_server()` polls `http://127.0.0.1:7432/api/health` until FastAPI responds (`main.py:20`).
3. pywebview opens `http://127.0.0.1:7432`; if pywebview is missing, the user is told to open the browser URL (`main.py:43`).
4. FastAPI serves API routers and, when present, mounts `frontend/dist` at `/` (`backend/main.py:21`, `backend/main.py:56`).

### Session Creation Path

1. Wizard components collect mode, dataset, output, annotations, model paths, classes, and confidence threshold into `useSessionStore` (`frontend/src/stores/sessionStore.ts:25`).
2. `StepModel` builds a `StartSessionRequest` and calls `api.session.start()` through Axios (`frontend/src/lib/api.ts:21`).
3. `start_session()` converts request data to `AnnotationSessionConfig` and validates data-root existence (`backend/api/session.py:35`).
4. `session_manager.start()` stops any existing tool and calls `_build_tool()` (`backend/services/session_manager.py:22`, `backend/services/session_manager.py:93`).
5. `_build_tool()` selects `AnnotationTool`, `OBBAnnotationTool`, or `ClassificationService` from `AnnotationTaskMode` (`backend/services/session_manager.py:93`).
6. The API returns `session_manager.get_state()`, including base64 frame bytes when a frame is renderable (`backend/services/session_manager.py:54`).

### Frame Interaction Path

1. `AnnotationCanvas` renders `state.frame_b64` as an image and overlays detections/ROI with SVG (`frontend/src/components/canvas/AnnotationCanvas.tsx:146`).
2. Mouse and keyboard handlers call `api.frame.*` endpoints for accept, reject, undo, manual detections, ROI, rotation, and source switching (`frontend/src/components/canvas/AnnotationCanvas.tsx:52`, `frontend/src/hooks/useKeyboard.ts:20`).
3. `backend/api/frame.py` fetches the active tool with `_require_tool()` and calls concrete tool methods such as `on_accept()`, `on_reject()`, `push_undo_state()`, `reset_roi()`, or `start_video()` (`backend/api/frame.py:39`, `backend/api/frame.py:62`).
4. Standard annotation `on_accept()` stores detections, writes annotations, remembers the saved record, and advances the frame pipeline (`backend/annotation/detection/workflow_actions.py:69`).
5. `FramePipelineMixin.load_next_frame()` autosaves, reads the next video/image frame, runs model inference/tracking, restores saved annotations, and refreshes display state (`backend/annotation/detection/frame_pipeline.py:39`).
6. API responses return the latest `SessionManager` snapshot and call `notify_frame_update()` so connected WebSocket clients receive the same state (`backend/api/frame.py:46`).

### Realtime State Path

1. `AppLayout` mounts `useWebSocket()` during annotation workspace rendering (`frontend/src/components/layout/AppLayout.tsx:10`).
2. `useWebSocket()` connects to `/ws`, retries after close, and stores valid state messages in `useAnnotationStore` (`frontend/src/hooks/useWebSocket.ts:9`).
3. `backend/api/ws.py` registers `_sync_broadcast` as a `SessionManager` frame listener at module import time (`backend/api/ws.py:45`).
4. `session_manager.notify_frame_update()` calls registered listeners with `get_state()` output (`backend/services/session_manager.py:80`).
5. `_broadcast()` sends serialized state to every active WebSocket connection and drops dead connections (`backend/api/ws.py:22`).

### Export Path

1. `ExportDialog` calls `api.export.run()` with split ratios, optional output directory, and augmentation factor (`frontend/src/lib/api.ts:58`).
2. `export_dataset()` verifies an active tool and dispatches to `tool.export()` for classification or `_run_annotation_export()` for annotation modes (`backend/api/export.py:26`).
3. Standard annotation export calls `tool.export_yolo_dataset()` implemented by `ExportActionsMixin` and lower-level exporters (`backend/api/export.py:53`, `backend/annotation/infrastructure/persistence/export_actions.py`).
4. Classification export writes a class-folder dataset through `export_classification_dataset()` (`backend/services/classification_service.py:96`, `backend/classification/dataset.py:343`).

**State Management:**
- Backend session state is mutable and process-local inside `session_manager` (`backend/services/session_manager.py`).
- Annotation tool state lives on mixin-composed tool instances (`backend/annotation/tool.py`, `backend/annotation_obb/tool.py`).
- Persistent output state is file-based COCO/classification JSON under `outputs/` (`backend/core/output_state.py`, `backend/classification/dataset.py`).
- Frontend state uses separate Zustand stores for session wizard data, annotation snapshots, and UI-only flags (`frontend/src/stores/sessionStore.ts`, `frontend/src/stores/annotationStore.ts`, `frontend/src/stores/uiStore.ts`).

## Key Abstractions

**AnnotationSessionConfig:**
- Purpose: Immutable configuration created by the wizard/API before a runtime tool starts.
- Examples: `backend/core/session.py`, `backend/api/session.py`, `backend/services/session_manager.py`
- Pattern: Frozen dataclass with normalization in `__post_init__`.

**AnnotationTaskMode:**
- Purpose: Enumerates workflow variants: `tracking`, `detection`, `obb`, and `classification`.
- Examples: `backend/core/session.py`, `backend/api/wizard.py`, `frontend/src/lib/types.ts`
- Pattern: String enum shared conceptually with TypeScript union type.

**SessionManager:**
- Purpose: Single runtime owner and state facade for all HTTP/WebSocket callers.
- Examples: `backend/services/session_manager.py`, `backend/api/frame.py`, `backend/api/ws.py`
- Pattern: Module-level singleton with a lock around lifecycle changes and callback listeners for state pushes.

**Mixin-Composed AnnotationTool:**
- Purpose: Combine UI-free annotation capabilities while keeping implementation modules scoped by workflow concern.
- Examples: `backend/annotation/tool.py`, `backend/annotation/state/core_init.py`, `backend/annotation/detection/frame_pipeline.py`
- Pattern: Multiple inheritance where mixins cooperate through `super().__init__()` and shared instance attributes imported from `backend/annotation/shared.py`.

**OBBDetection:**
- Purpose: Represent oriented bounding boxes with center, size, angle, confidence, category, and source.
- Examples: `backend/annotation_obb/geometry/obb_geometry.py`, `backend/annotation_obb/tool.py`
- Pattern: Dataclass plus geometry helper functions for conversion, clipping, and validation.

**Detection:**
- Purpose: Represent horizontal bounding boxes used by detection and tracking flows.
- Examples: `backend/models.py`, `backend/annotation/detection/frame_pipeline.py`, `backend/api/frame.py`
- Pattern: Dataclass containing original/warped bbox arrays and optional tracking identity.

**OutputState / LoadedAnnotationState:**
- Purpose: Summarize and load resumable annotation outputs.
- Examples: `backend/core/output_state.py`, `backend/api/wizard.py`
- Pattern: Frozen dataclasses backed by COCO JSON discovery functions.

**Frontend API Facade:**
- Purpose: Keep REST endpoint paths and response typing in one module.
- Examples: `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`
- Pattern: Exported object grouped by `session`, `frame`, `export`, and `wizard`.

## Entry Points

**Desktop App:**
- Location: `main.py`
- Triggers: `python main.py`, PyInstaller executable from `InoLabel.spec`.
- Responsibilities: Start local backend, wait for health, open webview or browser fallback.

**FastAPI Server:**
- Location: `backend/main.py`
- Triggers: Imported by `main.py`; run directly through `python build.py --dev` using `uvicorn backend.main:app`.
- Responsibilities: Register routers, expose health, serve production frontend build.

**Build Script:**
- Location: `build.py`
- Triggers: `python build.py`, `python build.py --frontend`, `python build.py --pyinst`, `python build.py --dev`.
- Responsibilities: Build Vite frontend, run PyInstaller, or start dev API server.

**PyInstaller Spec:**
- Location: `InoLabel.spec`
- Triggers: `build.py` PyInstaller call.
- Responsibilities: Bundle `frontend/dist`, `assets`, backend packages, Uvicorn/WebView dependencies, OpenCV/Numpy/SciPy/lapx, and Ultralytics dynamic files.

**React App:**
- Location: `frontend/src/main.tsx`, `frontend/src/App.tsx`
- Triggers: Vite dev server or static build served by FastAPI.
- Responsibilities: Mount React, switch between wizard and annotation workspace.

**Utilities:**
- Location: `utils/*.py`, `backend/utils/*.py`
- Triggers: Command-line utility execution.
- Responsibilities: Convert COCO to YOLO, convert tracking COCO to detection, augment output datasets, and merge YOLO splits.

## Architectural Constraints

- **Threading:** `main.py` runs Uvicorn in a daemon Python thread, while `backend/api/wizard.py` uses a single-worker `ThreadPoolExecutor` for native Tk file dialogs.
- **Async model:** FastAPI routers are `async`, but most annotation work is synchronous CPU/filesystem/OpenCV logic invoked directly inside handlers.
- **Global state:** `session_manager` in `backend/services/session_manager.py` is a module-level singleton; `_connections` in `backend/api/ws.py` is a module-level WebSocket set.
- **Runtime cardinality:** Only one active annotation/classification session exists per backend process.
- **Filesystem persistence:** Runtime output state is persisted to user-writable `outputs/` paths from `backend/config.py`.
- **Frontend API assumption:** The React API client uses relative `/api`; Vite proxies `/api` and `/ws` to `127.0.0.1:7432` in `frontend/vite.config.ts`.
- **Model loading:** YOLO weights are loaded lazily inside `CoreInitMixin.ensure_models_loaded()` (`backend/annotation/state/core_init.py`).
- **Circular imports:** No explicit circular import chain is detected in the scanned entry points; many annotation mixins share names through star imports from `backend/annotation/shared.py`, so add new mixins carefully.

## Anti-Patterns

### Bypassing SessionManager

**What happens:** API endpoints mutate `session_manager.tool` directly after retrieving it.
**Why it's wrong:** Direct mutations outside the active tool or `SessionManager` can skip lifecycle cleanup, state snapshots, and WebSocket notifications.
**Do this instead:** Add runtime behavior to the concrete tool or service, then call it through `session_manager` from the router and finish with `session_manager.notify_frame_update()` as in `backend/api/frame.py`.

### Adding New Workflow Behavior to Shared Imports

**What happens:** Many annotation modules use `from backend.annotation.shared import *`.
**Why it's wrong:** New shared symbols become implicit dependencies across mixins and make initialization order harder to reason about.
**Do this instead:** Place behavior in the relevant mixin directory, import explicit dependencies in that file when practical, and compose the mixin in `backend/annotation/tool.py` or `backend/annotation_obb/tool.py`.

### Duplicating Endpoint Paths in Components

**What happens:** Components can call backend routes directly with Axios or `fetch`.
**Why it's wrong:** It bypasses error normalization and makes endpoint changes harder.
**Do this instead:** Add or extend methods in `frontend/src/lib/api.ts`, then consume those methods from components/hooks.

### Writing Output Files Outside Output-State Helpers

**What happens:** New persistence code can create ad hoc paths under `outputs/`.
**Why it's wrong:** The wizard resume/template flow depends on discoverable annotation paths and output naming conventions.
**Do this instead:** Use `backend/core/output_state.py` for annotation outputs and `backend/classification/dataset.py` for classification outputs.

## Error Handling

**Strategy:** API routers convert validation and runtime failures to `HTTPException`; domain services print/log recoverable persistence and cleanup errors; the frontend Axios interceptor normalizes FastAPI `detail` into `error.message`.

**Patterns:**
- Raise `HTTPException(400, ...)` for invalid client state such as missing active sessions, bad paths, invalid ROI points, and invalid detection indexes (`backend/api/frame.py`, `backend/api/session.py`).
- Raise `HTTPException(500, str(exc))` around tool startup and export execution failures (`backend/api/session.py`, `backend/api/export.py`).
- Use broad exception guards for shutdown/autosave/resource cleanup to avoid crashing the process while preserving console messages (`backend/annotation/application/lifecycle.py`).
- Use frontend `try/catch` in interaction hooks/components and let API errors avoid corrupting local UI state (`frontend/src/hooks/useKeyboard.ts`, `frontend/src/components/canvas/AnnotationCanvas.tsx`).

## Cross-Cutting Concerns

**Logging:** `backend/main.py` configures Python logging globally; `backend/api/ws.py` uses `logging.getLogger(__name__)`; annotation lifecycle and services primarily use `print()` with `[INFO]`, `[AVISO]`, and `[ERRO]` prefixes.

**Validation:** Request shape validation uses Pydantic models in API files; session/domain validation uses `AnnotationSessionConfig.__post_init__()` and output-state loaders in `backend/core/`.

**Authentication:** Not applicable. The application is a local desktop/web tool; no authentication or authorization layer is detected.

**Packaging:** Production desktop packaging is centralized in `build.py` and `InoLabel.spec`; `backend/main.py` serves static `frontend/dist` when present.

**Configuration:** Runtime paths and defaults live in `backend/config.py`; user-selected paths/classes live in `AnnotationSessionConfig`; frontend development proxy config lives in `frontend/vite.config.ts`.

---

*Architecture analysis: 2026-05-29*
