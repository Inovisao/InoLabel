---
last_mapped_commit: af6f39f6d52b32e68a7d38ed4a1b747fd1283f01
---
<!-- refreshed: 2026-06-02 -->
# Architecture

**Analysis Date:** 2026-06-02

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                      User Entry Points                       │
├────────────────────┬────────────────────┬───────────────────┤
│ Tkinter Desktop UI │ FastAPI Backend     │ Tauri/React UI    │
│ `main.py`          │ `api_server.py`     │ `frontend/src`    │
│ `app/runner.py`   │ `app/api/main.py`   │ `frontend/src-tauri`│
└─────────┬──────────┴─────────┬──────────┴─────────┬─────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Session Layer                 │
│ `app/core/session.py`, `app/core/output_state.py`,           │
│ `app/core/startup_cache.py`, `app/api/state.py`              │
└─────────┬────────────────────┬────────────────────┬─────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                Annotation / Classification Workflows          │
│ `app/annotation/tool.py`, `app/annotation_obb/tool.py`,       │
│ `app/classification/tools/core.py`                           │
└─────────┬────────────────────┬────────────────────┬─────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain and Infrastructure                  │
│ `app/annotation/core`, `app/annotation/infrastructure`,       │
│ `app/annotation_obb/geometry`, `tracker`, `utils`             │
└─────────┬────────────────────┬────────────────────┬─────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                Filesystem Data, Exports, Runtime State        │
│ `assets`, `saved_data_states`, ignored `outputs/`,            │
│ ignored `dataset/`, ignored `models/`, ignored `.local/`      │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Desktop launcher | Runs the legacy Tkinter application and selects the workflow from startup configuration. | `main.py`, `app/runner.py` |
| API launcher | Starts uvicorn on `127.0.0.1:8765` for the frontend/Tauri path. | `api_server.py` |
| FastAPI app | Defines CORS, health endpoint, and router registration for sessions, frames, annotations, and classes. | `app/api/main.py` |
| API runtime state | Stores one in-process active session/config/tool placeholder shared by route handlers. | `app/api/state.py` |
| Session config | Validates task mode, source path, output path, model weights, classes, and confidence threshold. | `app/core/session.py` |
| Output state | Discovers, creates, resumes, and loads COCO-style annotation state directories. | `app/core/output_state.py` |
| Source discovery | Discovers supported videos, images, image folders, and image list files independent of UI widgets. | `app/sources/discovery.py` |
| HBB/tracking tool | Composes state, class, source, ROI, detection, persistence, lifecycle, and UI mixins. | `app/annotation/tool.py` |
| OBB tool | Reuses shared HBB UI/state pieces and replaces geometry, detection, persistence, and controls for oriented boxes. | `app/annotation_obb/tool.py` |
| Classification tool | Composes manual classification state, dataset, navigation, class actions, and UI mixins. | `app/classification/tools/core.py` |
| Frontend shell | Switches between wizard and annotation views based on Zustand session state. | `frontend/src/App.tsx` |
| Frontend API client | Wraps HTTP calls through `/api`, which Vite proxies to the Python server in development. | `frontend/src/api/client.ts`, `frontend/vite.config.ts` |
| Tauri shell | Spawns the Python API as an `api_server` sidecar and hosts the React bundle. | `frontend/src-tauri/src/lib.rs`, `frontend/src-tauri/tauri.conf.json` |

## Pattern Overview

**Overall:** Hybrid desktop architecture with mixin-composed Python workflows, a process-local FastAPI adapter, and an optional React/Tauri frontend.

**Key Characteristics:**
- Use `AnnotationSessionConfig` from `app/core/session.py` as the shared contract between startup UI, desktop workflows, and API session startup.
- Use composition root files (`app/annotation/tool.py`, `app/annotation_obb/tool.py`, `app/classification/tools/core.py`) to assemble workflow capabilities from mixins.
- Keep reusable non-widget services in `app/core`, `app/sources`, `app/annotation/core`, and `app/annotation/infrastructure`.
- Keep the current FastAPI server state in module-level singletons in `app/api/state.py`, `app/api/routes/frames.py`, and `app/api/routes/annotations.py`.
- Keep React state in Zustand stores in `frontend/src/stores/session.ts` and `frontend/src/stores/annotation.ts`.

## Layers

**Launch Layer:**
- Purpose: Start either the legacy desktop UI or the API server.
- Location: `main.py`, `api_server.py`, `app/runner.py`
- Contains: CLI-style process entry points and workflow class selection.
- Depends on: `app.ui.startup.splash`, `app.startup_dialog`, `app.annotation_tool`, `app.annotation_obb.tool`, `app.classification.tool`, `uvicorn`.
- Used by: Developer commands, PyInstaller builds, and Tauri sidecar startup.

**Session and Core Layer:**
- Purpose: Normalize configuration, persisted state discovery, output directory naming, and local startup cache.
- Location: `app/core/session.py`, `app/core/output_state.py`, `app/core/startup_cache.py`
- Contains: dataclasses, enums, path normalization, state file readers/writers, and cache readers/writers.
- Depends on: `app/config.py` for defaults.
- Used by: `app/ui/startup/wizard.py`, `app/runner.py`, `app/api/routes/session.py`, annotation tools, and tests.

**Desktop Workflow Layer:**
- Purpose: Implement interactive annotation/classification workflows.
- Location: `app/annotation`, `app/annotation_obb`, `app/classification/tools`
- Contains: state mixins, detection pipeline mixins, ROI mixins, persistence mixins, lifecycle mixins, Tkinter panels, and input handling.
- Depends on: `app/models.py`, `app/geometry.py`, `app/tracking`, root `tracker`, OpenCV, NumPy, YOLO, Pillow, and Tkinter.
- Used by: `app/runner.py` and compatibility imports in `app/annotation_tool.py`, `app/classification/tool.py`, and `app/annotation/__init__.py`.

**Domain Services Layer:**
- Purpose: Provide reusable non-UI operations for categories, augmentation, export formatting, OBB geometry, dataset classification, and source discovery.
- Location: `app/annotation/core`, `app/annotation/infrastructure/export`, `app/annotation_obb/geometry`, `app/annotation_obb/infrastructure/export`, `app/classification/dataset.py`, `app/sources/discovery.py`
- Contains: pure-ish functions, dataclasses, file export services, split services, and geometry helpers.
- Depends on: Standard library, NumPy/OpenCV where image geometry is required, and shared config constants.
- Used by: Desktop mixins, utility scripts, and tests.

**API Adapter Layer:**
- Purpose: Provide a JSON/HTTP interface for the React frontend.
- Location: `app/api/main.py`, `app/api/routes`, `app/api/schemas.py`, `app/api/state.py`
- Contains: FastAPI app, Pydantic schemas, session/frame/class/annotation routers, and process-local state.
- Depends on: `app/core/session.py`, OpenCV, NumPy, and FastAPI.
- Used by: `frontend/src/api/client.ts`, `frontend/src/stores/session.ts`, and `frontend/src/stores/annotation.ts`.

**Frontend Layer:**
- Purpose: Provide the newer web UI inside Vite/Tauri.
- Location: `frontend/src`
- Contains: React pages, components, Zustand stores, API types, API client, keyboard hook, styles.
- Depends on: React, Zustand, React Konva, Framer Motion, Lucide, and the FastAPI adapter.
- Used by: Vite dev server and Tauri application shell.

**Tauri Shell Layer:**
- Purpose: Package the React UI and launch the Python backend sidecar.
- Location: `frontend/src-tauri`
- Contains: Rust app bootstrap, Tauri config, Cargo manifest, build script.
- Depends on: `tauri_plugin_shell` and configured sidecar named `api_server`.
- Used by: `npm run tauri` from `frontend/package.json`.

## Data Flow

### Desktop Annotation Path

1. Process starts at `main.py:1` and calls `app.runner.main` in `app/runner.py:4`.
2. Startup UI returns an `AnnotationSessionConfig` through `app/startup_dialog.py` and `app/ui/startup/wizard.py:40`.
3. `app/runner.py:11` selects `AnnotationTool`, `OBBAnnotationTool`, or `ClassificationTool` based on `AnnotationTaskMode`.
4. `CoreInitMixin.__init__` in `app/annotation/state/core_init.py:4` validates paths, discovers sources, prepares output directories, initializes model/runtime state, builds the UI, and starts the first source.
5. `FramePipelineMixin.process_current_frame` in `app/annotation/detection/frame_pipeline.py:6` resets frame-local state, renders, and starts model inference in a daemon thread at `app/annotation/detection/frame_pipeline.py:58`.
6. `CocoStorageMixin.store_annotations` and `write_annotations` in `app/annotation/infrastructure/persistence/coco_storage.py` write images and COCO payloads under the configured output directory.

### Desktop Classification Path

1. `app/runner.py:14` selects `ClassificationTool` when mode is `AnnotationTaskMode.CLASSIFICATION`.
2. `ClassificationTool.__init__` in `app/classification/tools/core.py:20` loads image paths, creates class directories, loads prior state, builds Tkinter UI, and opens the first image.
3. Dataset operations in `app/classification/dataset.py` create class folders, persist `classification_state.json`, and export classified images.

### API and React/Tauri Path

1. `api_server.py:5` runs `app.api.main:app` through uvicorn on port `8765`.
2. `app/api/main.py:19` creates the FastAPI app and registers routers at `app/api/main.py:28` through `app/api/main.py:31`.
3. React starts at `frontend/src/main.tsx:6`; `frontend/src/App.tsx:5` renders the wizard or annotation view from Zustand session state.
4. `frontend/src/stores/session.ts:17` posts `/session/start`, then calls `/frames/init`.
5. `app/api/routes/session.py:13` validates the request into `AnnotationSessionConfig` and stores it in `app/api/state.py:25`.
6. `app/api/routes/frames.py:21` scans image paths into `_frame_paths`; frame endpoints return JPEG base64 payloads through `FrameResponse`.
7. `frontend/src/stores/annotation.ts:19` fetches frames/classes and posts/deletes in-memory annotations through `app/api/routes/annotations.py`.

**State Management:**
- Desktop state is instance state spread across mixins on the active tool object; initialization is centralized in `app/annotation/state/core_init.py` and `app/annotation/state/runtime_state.py`.
- API state is process-local module state: `runtime` in `app/api/state.py`, `_frame_paths` and `_current_index` in `app/api/routes/frames.py`, and `_store` plus `_next_id` in `app/api/routes/annotations.py`.
- Frontend state is held in Zustand stores at `frontend/src/stores/session.ts` and `frontend/src/stores/annotation.ts`.
- Persisted output state is JSON and image files managed by `app/core/output_state.py`, `app/annotation/infrastructure/persistence/coco_storage.py`, and `app/classification/dataset.py`.

## Key Abstractions

**AnnotationSessionConfig:**
- Purpose: Immutable session contract for task mode, data root, output path, weights, classes, resume flag, and confidence threshold.
- Examples: `app/core/session.py`, `app/api/routes/session.py`, `app/ui/startup/wizard.py`
- Pattern: Frozen dataclass with post-init normalization and validation.

**Mixin-Based Tool Composition:**
- Purpose: Split large UI workflows into capability modules while exposing one concrete tool class.
- Examples: `app/annotation/tool.py`, `app/annotation_obb/tool.py`, `app/classification/tools/core.py`
- Pattern: Multiple inheritance composition root; add new workflow capabilities by creating a focused mixin and including it in the appropriate tool class.

**COCO Payload Persistence:**
- Purpose: Keep images, annotations, categories, and annotation state in a serializable payload.
- Examples: `app/annotation/infrastructure/persistence/coco_storage.py`, `app/core/output_state.py`, `app/annotation/infrastructure/export/coco_exporter.py`
- Pattern: In-memory lists/dicts on the tool instance, serialized through `write_annotations`.

**OBB Geometry Model:**
- Purpose: Represent rotated boxes and convert between center-angle boxes, corner points, and HBB fallback geometry.
- Examples: `app/annotation_obb/geometry/obb_geometry.py`, `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py`
- Pattern: Dataclass plus pure conversion helpers.

**Frontend Store Contracts:**
- Purpose: Encapsulate async API calls and expose view state to React components.
- Examples: `frontend/src/stores/session.ts`, `frontend/src/stores/annotation.ts`, `frontend/src/api/types.ts`
- Pattern: Zustand store with typed actions that call `frontend/src/api/client.ts`.

## Entry Points

**Legacy Desktop App:**
- Location: `main.py`
- Triggers: `python main.py`, built executable, or PyInstaller output.
- Responsibilities: Delegate to `app.runner.main` and return process status.

**API Server:**
- Location: `api_server.py`
- Triggers: `python api_server.py`, uvicorn, or Tauri sidecar.
- Responsibilities: Host `app.api.main:app` on `127.0.0.1:8765`.

**FastAPI Application:**
- Location: `app/api/main.py`
- Triggers: Uvicorn import of `app`.
- Responsibilities: CORS setup, router registration, and `/health`.

**React Application:**
- Location: `frontend/src/main.tsx`
- Triggers: Vite dev server or Tauri webview bundle.
- Responsibilities: Mount `<App />` into `#root`.

**Tauri Application:**
- Location: `frontend/src-tauri/src/lib.rs`
- Triggers: `npm run tauri` or Tauri build output.
- Responsibilities: Install shell plugin and spawn the `api_server` sidecar.

**Utility Scripts:**
- Location: `utils/convert_coco_to_yolo_dataset.py`, `utils/convert_coco_tracking_to_detection.py`, `utils/augment_output_dataset.py`, `utils/merge_yolo_splits.py`
- Triggers: Manual CLI use.
- Responsibilities: Convert, augment, or merge generated datasets using `app/dataset_export.py` and related services.

## Architectural Constraints

- **Threading:** Tkinter workflows run on the main UI thread; inference/export work is offloaded through daemon threads in `app/annotation/detection/frame_pipeline.py`, `app/annotation/presentation/export/export_screen.py`, and startup preload in `app/ui/startup/splash.py`.
- **Global state:** The API is single-session and process-local through `app/api/state.py`, `_frame_paths` in `app/api/routes/frames.py`, and `_store` in `app/api/routes/annotations.py`.
- **Shared import hub:** Many annotation mixins use `from app.annotation.shared import *`; OBB mixins layer `app/annotation_obb/shared.py` on top of that hub.
- **Filesystem-first storage:** Dataset inputs, model weights, images, COCO JSON, YOLO exports, keybinds, and startup cache are all local filesystem resources configured in `app/config.py`.
- **Circular imports:** No explicit circular import chain was confirmed in the scan; lazy compatibility imports in `app/annotation/__init__.py` and `app/annotation_obb/__init__.py` should be kept when exposing tool classes.
- **API persistence:** The current API annotation router stores annotations only in memory in `app/api/routes/annotations.py`; it does not use `CocoStorageMixin`.

## Anti-Patterns

### Bypassing Composition Roots

**What happens:** Importing and instantiating lower-level mixins directly skips required initialization from `CoreInitMixin` or `ClassificationTool`.
**Why it's wrong:** Mixins assume instance fields such as `self.window`, `self.images`, `self.categories`, and tracker state already exist.
**Do this instead:** Add capabilities to `app/annotation/tool.py`, `app/annotation_obb/tool.py`, or `app/classification/tools/core.py`, then instantiate the concrete tool through `app/runner.py`.

### Adding Persistent API State to Route Modules

**What happens:** Route modules such as `app/api/routes/frames.py` and `app/api/routes/annotations.py` already hold module-level mutable state.
**Why it's wrong:** Additional globals make multi-session behavior and test isolation harder and diverge from persisted desktop state.
**Do this instead:** Put shared API session state behind `RuntimeState` in `app/api/state.py` or introduce a service object referenced from there.

### Reimplementing Export Formats in UI Code

**What happens:** Export logic can be placed directly in panels or button handlers.
**Why it's wrong:** Export behavior is already centralized and tested through service modules.
**Do this instead:** Add format logic under `app/annotation/core/export`, `app/annotation/infrastructure/export`, or `app/annotation_obb/infrastructure/export`, and call it from presentation mixins.

## Error Handling

**Strategy:** Validate early at session/config boundaries, raise typed HTTP errors in API routes, and catch broad desktop runtime failures at process/workflow boundaries.

**Patterns:**
- `AnnotationSessionConfig.__post_init__` in `app/core/session.py` raises `ValueError` for invalid classes or confidence threshold.
- `app/runner.py` catches `KeyboardInterrupt` and broad exceptions, calls `finish_processing`, prints to stderr, and returns a non-zero process code.
- API routes raise `HTTPException` for missing frames, invalid frame indexes, unreadable images, and missing annotations.
- State loaders in `app/core/output_state.py` and `app/core/startup_cache.py` tolerate malformed or missing state/cache files where user recovery is expected.

## Cross-Cutting Concerns

**Logging:** Uses `print` statements in desktop workflows and uvicorn/FastAPI logging for the API server; no centralized logging adapter was detected.

**Validation:** Uses dataclass normalization in `app/core/session.py`, Pydantic schemas in `app/api/schemas.py`, and path/file checks in source discovery and state loading modules.

**Authentication:** Not applicable; no authentication layer is present in `app/api/main.py` or frontend API calls.

**Configuration:** Uses constants in `app/config.py`, user-local cache in `.local/startup_cache.json` via `app/core/startup_cache.py`, Vite config in `frontend/vite.config.ts`, and Tauri config in `frontend/src-tauri/tauri.conf.json`.

---

*Architecture analysis: 2026-06-02*
