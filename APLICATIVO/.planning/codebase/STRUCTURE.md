---
last_mapped_commit: af6f39f6d52b32e68a7d38ed4a1b747fd1283f01
---
# Codebase Structure

**Analysis Date:** 2026-06-02

## Directory Layout

```text
InoLabel/
├── .github/workflows/        # CI workflow definitions
├── .planning/codebase/       # Generated GSD codebase maps
├── app/                      # Python application package
│   ├── annotation/           # HBB/tracking annotation workflow
│   ├── annotation_obb/       # Oriented bounding box workflow
│   ├── api/                  # FastAPI backend for React/Tauri UI
│   ├── classification/       # Manual image classification workflow
│   ├── core/                 # Shared session, output, and startup-cache services
│   ├── sources/              # UI-independent source discovery
│   ├── tracking/             # App wrapper around multi-class ByteTrack behavior
│   └── ui/                   # Tkinter shared components, layout, startup, and theme
├── assets/                   # Bundled static assets
├── frontend/                 # React/Vite/Tauri frontend
│   ├── src/                  # React application source
│   └── src-tauri/            # Rust/Tauri shell and sidecar config
├── saved_data_states/        # Runtime annotation state directory
├── tests/                    # Python unittest test suite
├── tracker/                  # ByteTrack implementation modules
├── utils/                    # Dataset conversion and augmentation CLI utilities
├── api_server.py             # API process entry point
├── main.py                   # Legacy desktop process entry point
├── build.sh                  # Cross-platform build/package script
├── requirements.txt          # Python dependencies
└── README.md                 # User/developer guide
```

## Directory Purposes

**`app`:**
- Purpose: Main Python package for the desktop app, API adapter, domain services, and UI.
- Contains: Workflow composition roots, mixins, FastAPI routers, shared dataclasses, export services, geometry helpers, and Tkinter UI modules.
- Key files: `app/runner.py`, `app/config.py`, `app/core/session.py`, `app/annotation/tool.py`, `app/annotation_obb/tool.py`, `app/classification/tools/core.py`, `app/api/main.py`

**`app/annotation`:**
- Purpose: Horizontal bounding box detection/tracking workflow for videos, image folders, single images, and image lists.
- Contains: Mixin groups for application lifecycle, core services, detection, persistence, keybinds, presentation panels, ROI, source loading, runtime state, and UI rendering.
- Key files: `app/annotation/tool.py`, `app/annotation/shared.py`, `app/annotation/state/core_init.py`, `app/annotation/detection/frame_pipeline.py`, `app/annotation/infrastructure/persistence/coco_storage.py`

**`app/annotation/core`:**
- Purpose: Workflow-domain services that are not tied directly to Tkinter panels.
- Contains: Augmentation service/types, export value types, split service, YOLO label formatting, and class service mixins.
- Key files: `app/annotation/core/augmentation/augmentation_service.py`, `app/annotation/core/export/yolo_label_service.py`, `app/annotation/core/export/split_service.py`, `app/annotation/core/services/class_service.py`

**`app/annotation/infrastructure`:**
- Purpose: Filesystem persistence and export implementations for annotation data.
- Contains: COCO exporter, YOLO exporter, COCO storage mixin, and export actions mixin.
- Key files: `app/annotation/infrastructure/export/coco_exporter.py`, `app/annotation/infrastructure/export/yolo_exporter.py`, `app/annotation/infrastructure/persistence/coco_storage.py`, `app/annotation/infrastructure/persistence/export_actions.py`

**`app/annotation/presentation`:**
- Purpose: Tkinter window panels, widgets, and export screens for annotation workflows.
- Contains: Main window, topbar, sidebar, statusbar, canvas panel, class panel widget, export UI, preview dialog.
- Key files: `app/annotation/presentation/panels/main_window.py`, `app/annotation/presentation/panels/sidebar_panel.py`, `app/annotation/presentation/export/export_screen.py`, `app/annotation/presentation/widgets/class_panel_widget.py`

**`app/annotation/ui`:**
- Purpose: Annotation canvas rendering, overlay drawing, status rendering, mouse handling, mode toggles, and control binding.
- Contains: Display/control mixins and geometry helpers for visual rotation.
- Key files: `app/annotation/ui/display_canvas.py`, `app/annotation/ui/display_overlays.py`, `app/annotation/ui/mouse_events.py`, `app/annotation/ui/ui_controls.py`, `app/annotation/ui/rotation_utils.py`

**`app/annotation_obb`:**
- Purpose: OBB-specific workflow that reuses shared annotation components and replaces oriented-box-specific behavior.
- Contains: OBB detection, geometry, export, persistence, source helpers, runtime state, and UI controls/renderers.
- Key files: `app/annotation_obb/tool.py`, `app/annotation_obb/shared.py`, `app/annotation_obb/geometry/obb_geometry.py`, `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py`, `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`

**`app/api`:**
- Purpose: FastAPI adapter for the React/Tauri interface.
- Contains: App setup, Pydantic schemas, global runtime state, and route modules.
- Key files: `app/api/main.py`, `app/api/state.py`, `app/api/schemas.py`, `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `app/api/routes/classes.py`

**`app/classification`:**
- Purpose: Manual image classification workflow and dataset operations.
- Contains: Dataset state helpers plus mixins for class actions, dataset actions, navigation, state, and UI.
- Key files: `app/classification/dataset.py`, `app/classification/tools/core.py`, `app/classification/tools/state.py`, `app/classification/tools/ui.py`, `app/classification/tool.py`

**`app/core`:**
- Purpose: Shared configuration objects and persisted state discovery used by multiple workflows.
- Contains: Session dataclasses/enums, output annotation state helpers, startup cache helpers.
- Key files: `app/core/session.py`, `app/core/output_state.py`, `app/core/startup_cache.py`

**`app/sources`:**
- Purpose: Source discovery decoupled from UI-specific source loading mixins.
- Contains: `SourceSummary` and `SourceDiscoveryService`.
- Key files: `app/sources/discovery.py`, `app/sources/__init__.py`

**`app/ui`:**
- Purpose: Shared Tkinter UI building blocks and startup flow.
- Contains: Component factories, file manager, responsive layout helpers, startup splash/intro/wizard, theme tokens, and palette.
- Key files: `app/ui/components/button.py`, `app/ui/components/card.py`, `app/ui/layout/responsive_window.py`, `app/ui/startup/wizard.py`, `app/ui/theme/tokens.py`

**`frontend/src`:**
- Purpose: React frontend for session setup and annotation UI.
- Contains: API types/client, canvas/layout/wizard components, keyboard hook, pages, Zustand stores, and CSS.
- Key files: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/stores/session.ts`, `frontend/src/stores/annotation.ts`, `frontend/src/components/canvas/AnnotationCanvas.tsx`

**`frontend/src-tauri`:**
- Purpose: Native shell for the React UI and Python API sidecar.
- Contains: Tauri config, Cargo manifest, build script, and Rust launcher.
- Key files: `frontend/src-tauri/tauri.conf.json`, `frontend/src-tauri/src/lib.rs`, `frontend/src-tauri/src/main.rs`, `frontend/src-tauri/Cargo.toml`

**`tests`:**
- Purpose: Python regression tests for session config, output state, exports, UI helpers, OBB geometry, keybinds, classification, and tracking fallbacks.
- Contains: `unittest` modules named `test_*.py`.
- Key files: `tests/test_session_config.py`, `tests/test_dataset_export.py`, `tests/test_yolo_obb_export.py`, `tests/test_classification_dataset.py`, `tests/test_keybinds.py`

**`tracker`:**
- Purpose: Low-level ByteTrack modules.
- Contains: Base track, BYTETracker, Kalman filter, and matching helpers.
- Key files: `tracker/byte_tracker.py`, `tracker/basetrack.py`, `tracker/kalman_filter.py`, `tracker/matching.py`

**`utils`:**
- Purpose: Manual CLI utilities for generated dataset conversion, augmentation, and merge operations.
- Contains: Standalone scripts that import app export services.
- Key files: `utils/convert_coco_to_yolo_dataset.py`, `utils/convert_coco_tracking_to_detection.py`, `utils/augment_output_dataset.py`, `utils/merge_yolo_splits.py`

## Key File Locations

**Entry Points:**
- `main.py`: Starts the legacy Tkinter desktop workflow by delegating to `app/runner.py`.
- `app/runner.py`: Shows startup splash/config and selects `AnnotationTool`, `OBBAnnotationTool`, or `ClassificationTool`.
- `api_server.py`: Starts `app.api.main:app` with uvicorn.
- `app/api/main.py`: Defines the FastAPI app and registers routers.
- `frontend/src/main.tsx`: Mounts React into `#root`.
- `frontend/src-tauri/src/lib.rs`: Starts Tauri and spawns the `api_server` sidecar.

**Configuration:**
- `app/config.py`: Python defaults for paths, model/data locations, thresholds, rendering flags, and UI margins.
- `requirements.txt`: Python dependency list.
- `frontend/package.json`: Frontend dependencies and scripts.
- `frontend/vite.config.ts`: Vite plugins, dev port, `/api` proxy, and build target.
- `frontend/src-tauri/tauri.conf.json`: Tauri window, build, bundle, and sidecar settings.
- `.github/workflows/ci.yml`: CI workflow definition.
- `.gitignore`: Ignored runtime data, local config, build output, caches, AI tool folders, logs, and frontend generated directories.

**Core Logic:**
- `app/core/session.py`: Task modes and validated session config.
- `app/core/output_state.py`: Annotation output state discovery/load/create helpers.
- `app/sources/discovery.py`: UI-independent source discovery.
- `app/annotation/tool.py`: HBB/tracking annotation composition root.
- `app/annotation_obb/tool.py`: OBB annotation composition root.
- `app/classification/tools/core.py`: Classification composition root.
- `app/annotation/detection/frame_pipeline.py`: Frame processing, model inference, tracking, and detection creation.
- `app/annotation/infrastructure/persistence/coco_storage.py`: COCO payload storage and image writing.
- `app/annotation_obb/geometry/obb_geometry.py`: OBB dataclass and geometry conversions.
- `app/classification/dataset.py`: Classification state and dataset filesystem operations.

**Frontend Logic:**
- `frontend/src/App.tsx`: Top-level wizard vs annotation route switch.
- `frontend/src/api/client.ts`: Fetch wrapper for `/api`.
- `frontend/src/api/types.ts`: TypeScript API contracts.
- `frontend/src/stores/session.ts`: Session lifecycle state and API calls.
- `frontend/src/stores/annotation.ts`: Current frame, classes, selected class, and annotation API calls.
- `frontend/src/pages/WizardPage.tsx`: Wizard page wrapper.
- `frontend/src/pages/AnnotatePage.tsx`: Annotation screen layout and data bootstrapping.
- `frontend/src/components/canvas/AnnotationCanvas.tsx`: React Konva annotation canvas.

**Testing:**
- `tests/test_session_config.py`: Session config and source discovery behavior.
- `tests/test_output_state.py`: Output state discovery/loading behavior.
- `tests/test_dataset_export.py`: COCO/YOLO export and annotation workflow behavior.
- `tests/test_yolo_obb_export.py`: OBB YOLO export behavior.
- `tests/test_classification_dataset.py`: Classification dataset/state behavior.
- `tests/test_obb_geometry.py`: OBB geometry conversions.
- `tests/test_keybinds.py`: Keybind mapping/repository/service behavior.
- `tests/test_components.py`: Tkinter component helper behavior.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`: `app/core/output_state.py`, `app/annotation/detection/frame_pipeline.py`, `app/ui/layout/responsive_window.py`.
- Workflow composition roots are named `tool.py` or `core.py`: `app/annotation/tool.py`, `app/annotation_obb/tool.py`, `app/classification/tools/core.py`.
- Mixin modules are named by capability: `app/annotation/ui/display_canvas.py`, `app/annotation/detection/selection_edit.py`, `app/classification/tools/navigation.py`.
- Tests use `test_*.py`: `tests/test_startup_cache.py`, `tests/test_theme_compat.py`.
- React components use `PascalCase.tsx`: `frontend/src/components/wizard/Wizard.tsx`, `frontend/src/pages/AnnotatePage.tsx`.
- React stores and hooks use `camelCase.ts` or domain names: `frontend/src/stores/session.ts`, `frontend/src/hooks/useKeyboardShortcuts.ts`.
- Tauri/Rust files follow Rust defaults: `frontend/src-tauri/src/lib.rs`, `frontend/src-tauri/src/main.rs`.

**Directories:**
- Python package directories use lowercase names, with underscores for multi-word domains: `app/annotation_obb`, `app/core`, `app/ui`.
- Layer directories under annotation use role names: `application`, `core`, `detection`, `infrastructure`, `presentation`, `roi`, `sources`, `state`, `ui`.
- Frontend directories group by responsibility: `frontend/src/api`, `frontend/src/components`, `frontend/src/hooks`, `frontend/src/pages`, `frontend/src/stores`.

## Where to Add New Code

**New HBB/Tracking Annotation Capability:**
- Primary code: Add a focused mixin under the relevant `app/annotation` subdirectory.
- Composition: Include the mixin in `app/annotation/tool.py` when it must be part of the concrete tool.
- UI panel/widget code: `app/annotation/presentation/panels` or `app/annotation/presentation/widgets`.
- Rendering/input code: `app/annotation/ui`.
- Persistence/export code: `app/annotation/infrastructure/persistence` or `app/annotation/infrastructure/export`.
- Tests: Add targeted tests under `tests/test_*.py`.

**New OBB Capability:**
- Primary code: Add OBB-specific logic under `app/annotation_obb`.
- Shared HBB reuse: Import existing shared mixins only when OBB behavior is identical.
- Geometry/export code: `app/annotation_obb/geometry` or `app/annotation_obb/infrastructure/export`.
- Composition: Include new mixins in `app/annotation_obb/tool.py`.
- Tests: Add or extend `tests/test_obb_geometry.py`, `tests/test_yolo_obb_export.py`, or a new `tests/test_obb_*.py`.

**New Classification Feature:**
- Primary code: Add dataset/state logic to `app/classification/dataset.py` when it is independent of Tkinter.
- UI/action code: Add mixins under `app/classification/tools`.
- Composition: Include new mixins in `app/classification/tools/core.py`.
- Compatibility exports: Keep `app/classification/tool.py` as a thin compatibility wrapper.
- Tests: Add or extend `tests/test_classification_dataset.py`.

**New API Endpoint:**
- Schema: Add Pydantic request/response types to `app/api/schemas.py`.
- Route: Add or extend a router in `app/api/routes`.
- App registration: Register new routers in `app/api/main.py`.
- Shared state: Put cross-route state in `app/api/state.py`.
- Frontend client/types: Mirror contracts in `frontend/src/api/types.ts` and call through `frontend/src/api/client.ts`.
- Frontend store: Add API-driven state/actions under `frontend/src/stores`.

**New React UI View or Component:**
- Page-level screen: `frontend/src/pages`.
- Reusable UI region: `frontend/src/components`.
- Wizard step: `frontend/src/components/wizard`.
- Annotation canvas behavior: `frontend/src/components/canvas`.
- Cross-component state: `frontend/src/stores`.
- Server calls: `frontend/src/api/client.ts` and `frontend/src/api/types.ts`.

**New Shared Utility or Service:**
- Session/output/source concerns: `app/core` or `app/sources`.
- Geometry/model-independent helpers: `app/geometry.py` or a focused module under the workflow package.
- Export formatting: `app/annotation/core/export`, `app/annotation/infrastructure/export`, or `app/annotation_obb/infrastructure/export`.
- One-off CLI utilities: `utils`.

**New Tests:**
- Python tests: Add `tests/test_<area>.py`.
- Prefer testing domain services and persistence/export helpers directly rather than opening full Tkinter windows.
- Frontend tests: Not detected in current structure; add frontend test tooling before adding frontend test files.

## Special Directories

**`.planning/codebase`:**
- Purpose: GSD architecture, stack, quality, and concerns maps.
- Generated: Yes.
- Committed: Project-controlled planning artifact directory.

**`assets`:**
- Purpose: Static bundled assets such as `assets/inovisao.png`.
- Generated: No.
- Committed: Yes.

**`saved_data_states`:**
- Purpose: Runtime annotation state location used by the application.
- Generated: Yes.
- Committed: Directory present; runtime contents should be treated as data, not source code.

**`.local`:**
- Purpose: User-local startup cache and keybinds used by `app/core/startup_cache.py` and keybind repository code.
- Generated: Yes.
- Committed: No; ignored by `.gitignore`.

**`outputs`, `dataset`, `data`, `models`, `videos`, `imagens`, `dataset_original`:**
- Purpose: Local user data, generated outputs, and model/data assets.
- Generated: User/runtime supplied.
- Committed: No; ignored by `.gitignore`.

**`dist`, `build`, `frontend/dist`, `frontend/src-tauri/target`, `frontend/.tauri`:**
- Purpose: Build and packaging outputs for Python, frontend, and Tauri.
- Generated: Yes.
- Committed: No; ignored by `.gitignore`.

**`__pycache__`, `.pytest_cache`, `frontend/node_modules`:**
- Purpose: Runtime/test/package-manager caches.
- Generated: Yes.
- Committed: No; ignored by `.gitignore`.

**`tracker`:**
- Purpose: Vendored or local ByteTrack algorithm implementation used by `app/tracking/multiclass_byte_tracking.py` and annotation runtime.
- Generated: No.
- Committed: Yes.

---

*Structure analysis: 2026-06-02*
