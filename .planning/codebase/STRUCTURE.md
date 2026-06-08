# Codebase Structure

**Analysis Date:** 2026-06-08

## Directory Layout

```text
InoLabel/
|-- app/                         # Python application package: API, core services, annotation/export logic
|   |-- api/                     # FastAPI app, schemas, process state, and route modules
|   |-- annotation/              # Legacy standard bbox annotation mixins and export/persistence services
|   |-- annotation_obb/          # OBB-specific annotation, geometry, export, and persistence modules
|   |-- classification/          # Classification dataset helpers and legacy UI mixins
|   |-- core/                    # Session config, export jobs, startup/output helpers, detector/tracker wrappers
|   |-- sources/                 # UI-independent source discovery
|   `-- tracking/                # App-level multiclass tracking wrapper
|-- frontend/                    # React/Vite WebUI and Tauri desktop shell
|   |-- src/                     # React app, pages, stores, API types/client, components, CSS
|   |-- public/                  # Static frontend assets
|   `-- src-tauri/               # Tauri Rust shell and packaging config
|-- tracker/                     # BYTETracker implementation and matching/Kalman helpers
|-- tests/                       # Python tests for API, exports, geometry, sessions, UI compatibility, tracking
|-- utils/                       # Standalone dataset conversion/augmentation and legacy annotation scripts
|-- .github/workflows/           # GitHub Actions workflows
|-- .planning/codebase/          # GSD-generated codebase maps
|-- output/                      # Runtime output directory
|-- saved_data_states/           # Runtime saved-state directory
|-- APLICATIVO/                  # Packaged application output
|-- build/                       # PyInstaller/build output
|-- dist/                        # Distribution output
|-- main.py                      # Web app launcher with browser opening
|-- api_server.py                # Backend-only launcher
|-- requirements.txt             # Python dependency list
|-- frontend/package.json        # Frontend dependencies and scripts
`-- InoLabel.spec                 # PyInstaller spec file
```

## Directory Purposes

**`app/`:**
- Purpose: Primary Python source package for backend API, domain services, legacy annotation logic, export logic, and configuration.
- Contains: `app/api/*`, `app/core/*`, `app/annotation/*`, `app/annotation_obb/*`, `app/classification/*`, `app/sources/*`, `app/tracking/*`, `app/config.py`, `app/models.py`, `app/geometry.py`, `app/dataset_export.py`.
- Key files: `app/api/main.py`, `app/api/state.py`, `app/api/schemas.py`, `app/config.py`, `app/core/session.py`, `app/core/exporter.py`.

**`app/api/`:**
- Purpose: FastAPI WebUI backend.
- Contains: `app/api/main.py` app composition, `app/api/schemas.py` Pydantic models, `app/api/state.py` process-local state, and `app/api/routes/*`.
- Key files: `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `app/api/routes/export.py`, `app/api/routes/validation.py`.

**`app/api/routes/`:**
- Purpose: One `APIRouter` module per API concern.
- Contains: Session lifecycle, file/path validation, frame navigation, annotation CRUD/autosave, class listing, keybind profile persistence, native file browsing, export start/progress.
- Key files: `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `app/api/routes/export.py`, `app/api/routes/browse.py`, `app/api/routes/keybinds.py`.

**`app/core/`:**
- Purpose: Backend/domain primitives shared by API routes, tests, and legacy code.
- Contains: Session config, export job metadata, startup cache, output-state helpers, tracker/detector wrappers, palette.
- Key files: `app/core/session.py`, `app/core/exporter.py`, `app/core/output_state.py`, `app/core/startup_cache.py`, `app/core/palette.py`.

**`app/sources/`:**
- Purpose: UI-independent dataset/source discovery.
- Contains: `SourceDiscoveryService` and `SourceSummary`.
- Key files: `app/sources/discovery.py`, `app/sources/__init__.py`.

**`app/annotation/`:**
- Purpose: Legacy standard bbox annotation source, shared dependencies, mixins, and export/persistence services.
- Contains: `app/annotation/shared.py`, `app/annotation/detection/*`, `app/annotation/state/*`, `app/annotation/sources/*`, `app/annotation/roi/*`, `app/annotation/keybinds/*`, `app/annotation/core/*`, `app/annotation/infrastructure/*`.
- Key files: `app/annotation/shared.py`, `app/annotation/detection/__init__.py`, `app/annotation/infrastructure/export/yolo_exporter.py`, `app/annotation/infrastructure/export/coco_exporter.py`, `app/annotation/infrastructure/persistence/coco_storage.py`.

**`app/annotation/core/`:**
- Purpose: Annotation-domain services and value objects independent from concrete persistence/export callers.
- Contains: Augmentation types/services, export split/label helpers, class service.
- Key files: `app/annotation/core/augmentation/augmentation_service.py`, `app/annotation/core/augmentation/augmentation_types.py`, `app/annotation/core/export/split_service.py`, `app/annotation/core/export/yolo_label_service.py`, `app/annotation/core/services/class_service.py`.

**`app/annotation/infrastructure/`:**
- Purpose: Concrete export and persistence implementations for standard bbox annotations.
- Contains: COCO/YOLO exporters and persistence mixins.
- Key files: `app/annotation/infrastructure/export/yolo_exporter.py`, `app/annotation/infrastructure/export/coco_exporter.py`, `app/annotation/infrastructure/persistence/export_actions.py`, `app/annotation/infrastructure/persistence/coco_storage.py`.

**`app/annotation_obb/`:**
- Purpose: OBB-specific annotation behavior, geometry, export, and persistence.
- Contains: OBB shared imports, geometry functions, detection/state/source mixins, OBB YOLO exporter, OBB persistence.
- Key files: `app/annotation_obb/geometry/obb_geometry.py`, `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py`, `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`.

**`app/classification/`:**
- Purpose: Classification dataset and legacy classification tool behavior.
- Contains: Dataset export/loading helpers and tool mixins for state, class actions, dataset actions, and navigation.
- Key files: `app/classification/dataset.py`, `app/classification/tools/state.py`, `app/classification/tools/class_actions.py`, `app/classification/tools/dataset_actions.py`, `app/classification/tools/navigation.py`.

**`app/tracking/`:**
- Purpose: Application wrapper around tracking implementation.
- Contains: Multiclass BYTETracker wrapper and package export.
- Key files: `app/tracking/multiclass_byte_tracking.py`, `app/tracking/__init__.py`.

**`tracker/`:**
- Purpose: Vendored or local BYTETracker implementation.
- Contains: Base track, BYTETracker, Kalman filter, matching helpers.
- Key files: `tracker/byte_tracker.py`, `tracker/matching.py`, `tracker/kalman_filter.py`, `tracker/basetrack.py`.

**`frontend/`:**
- Purpose: React/Vite WebUI and Tauri wrapper.
- Contains: `frontend/src/*`, `frontend/public/*`, `frontend/src-tauri/*`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`.
- Key files: `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/api/client.ts`, `frontend/src/stores/session.ts`, `frontend/src/stores/annotation.ts`.

**`frontend/src/`:**
- Purpose: Frontend application source.
- Contains: Pages, layout/canvas/modal/wizard components, Zustand stores, API types/client, hooks, toast context, CSS.
- Key files: `frontend/src/App.tsx`, `frontend/src/pages/AnnotatePage.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/components/wizard/Wizard.tsx`, `frontend/src/components/modals/ExportModal.tsx`.

**`frontend/src-tauri/`:**
- Purpose: Desktop shell and bundling configuration for the frontend.
- Contains: Rust app entry point, Tauri config, Cargo manifest, build script.
- Key files: `frontend/src-tauri/tauri.conf.json`, `frontend/src-tauri/src/lib.rs`, `frontend/src-tauri/src/main.rs`, `frontend/src-tauri/Cargo.toml`.

**`tests/`:**
- Purpose: Python test suite for API behavior, exports, session/config, geometry, tracking, keybinds, and legacy UI compatibility.
- Contains: `test_*.py` and `main_test.py`.
- Key files: `tests/test_api_contract.py`, `tests/test_dataset_export.py`, `tests/test_yolo_obb_export.py`, `tests/test_session_config.py`, `tests/test_tracker_matching_fallbacks.py`.

**`utils/`:**
- Purpose: Standalone operational scripts for dataset conversion, split merging, augmentation, and legacy annotation.
- Contains: Python scripts with direct `main()` entry points.
- Key files: `utils/merge_yolo_splits.py`, `utils/convert_coco_to_yolo_dataset.py`, `utils/convert_coco_tracking_to_detection.py`, `utils/augment_output_dataset.py`, `utils/annotation_tool_bytetracked.py`.

**Generated/Distribution Directories:**
- Purpose: Generated outputs or packaged application artifacts.
- Contains: `APLICATIVO/`, `build/`, `dist/`, `output/`, `saved_data_states/`, `frontend/dist/`, `frontend/src-tauri/target/`.
- Key files: `APLICATIVO/InoLabel/*`, `build/*`, `dist/*`.

## Key File Locations

**Entry Points:**
- `main.py`: Starts uvicorn on `127.0.0.1:8765`, waits for `/health`, and opens the browser.
- `api_server.py`: Starts the backend API without browser-opening behavior.
- `app/api/main.py`: FastAPI app composition root.
- `frontend/src/main.tsx`: React render entry point.
- `frontend/src/App.tsx`: Frontend view router and active-session switch.
- `frontend/src-tauri/src/main.rs`: Tauri native entry point.
- `utils/*.py`: CLI script entry points for dataset utilities.

**Configuration:**
- `requirements.txt`: Python runtime dependencies.
- `frontend/package.json`: Frontend dependencies and npm scripts.
- `frontend/vite.config.ts`: Vite dev/build config, `/api` proxy, and frontend build settings.
- `frontend/tsconfig.json`: TypeScript compiler config.
- `frontend/src-tauri/tauri.conf.json`: Tauri app/window/bundle config.
- `app/config.py`: Runtime filesystem paths, file extensions, model/output paths, confidence defaults, and PyInstaller path handling.
- `InoLabel.spec`: PyInstaller packaging config.
- `.gitignore`: Generated output, data/model, cache, IDE, docs, frontend build, and Tauri target ignore rules.

**Core Logic:**
- `app/api/routes/session.py`: Session lifecycle and metadata writes.
- `app/api/routes/frames.py`: Frame discovery, encoding, dimensions, and navigation.
- `app/api/routes/annotations.py`: Annotation store access and YOLO autosave.
- `app/api/routes/export.py`: Export job creation, staging, and progress updates.
- `app/api/state.py`: Shared process-local backend state.
- `app/api/schemas.py`: HTTP schema definitions.
- `app/core/session.py`: Annotation task modes and immutable session config.
- `app/core/exporter.py`: Export job model and split validation.
- `app/sources/discovery.py`: Dataset source discovery.
- `app/annotation/infrastructure/export/yolo_exporter.py`: Standard YOLO export.
- `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py`: OBB YOLO export.
- `tracker/byte_tracker.py`: BYTETracker implementation.

**Frontend Logic:**
- `frontend/src/api/client.ts`: Fetch wrapper and API error normalization.
- `frontend/src/api/types.ts`: Frontend API contract interfaces.
- `frontend/src/stores/session.ts`: Session lifecycle store.
- `frontend/src/stores/annotation.ts`: Frame/class/annotation store.
- `frontend/src/components/canvas/AnnotationCanvas.tsx`: Image rendering and bbox drawing.
- `frontend/src/components/modals/ExportModal.tsx`: Export request/progress UI.
- `frontend/src/components/wizard/Wizard.tsx`: Session setup wizard.
- `frontend/src/pages/AnnotatePage.tsx`: Active annotation workspace composition.

**Testing:**
- `tests/test_api_contract.py`: FastAPI import boundary, route contract, session lifecycle, export lifecycle, keybinds, config paths.
- `tests/test_dataset_export.py`: Dataset export behavior.
- `tests/test_yolo_obb_export.py`: OBB export behavior.
- `tests/test_obb_geometry.py`: OBB geometry conversions.
- `tests/test_session_config.py`: Session config validation.
- `tests/test_tracker_matching_fallbacks.py`: Tracker matching behavior.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`: `app/api/routes/session.py`, `app/core/output_state.py`, `app/annotation/infrastructure/export/yolo_exporter.py`.
- Python tests use `test_*.py`: `tests/test_api_contract.py`, `tests/test_session_config.py`.
- React components and pages use `PascalCase.tsx`: `frontend/src/App.tsx`, `frontend/src/pages/AnnotatePage.tsx`, `frontend/src/components/modals/ExportModal.tsx`.
- React hooks use `use*.ts`: `frontend/src/hooks/useKeyboardShortcuts.ts`.
- Zustand stores use lower-case noun files: `frontend/src/stores/session.ts`, `frontend/src/stores/annotation.ts`.
- Frontend API contract modules use descriptive lower-case names: `frontend/src/api/client.ts`, `frontend/src/api/types.ts`.

**Directories:**
- Python package directories are lower-case domain names: `app/api`, `app/core`, `app/sources`, `app/tracking`, `tracker`, `utils`.
- Feature subpackages group by concern: `app/annotation/detection`, `app/annotation/state`, `app/annotation/infrastructure/export`, `app/annotation/core/export`.
- Frontend directories group by UI role: `frontend/src/pages`, `frontend/src/components/layout`, `frontend/src/components/modals`, `frontend/src/components/wizard`, `frontend/src/components/canvas`, `frontend/src/stores`, `frontend/src/api`.
- Tauri code stays under `frontend/src-tauri`.

## Where to Add New Code

**New API Endpoint:**
- Primary code: Add a route module under `app/api/routes/` or extend the closest existing module, then register the router in `app/api/main.py`.
- Schemas: Add request/response models to `app/api/schemas.py`.
- State: Add process-local state and reset behavior in `app/api/state.py`.
- Tests: Add API contract tests under `tests/test_api_contract.py` or a focused `tests/test_<feature>.py`.

**New Session Or Workflow Behavior:**
- Backend lifecycle: Extend `app/api/routes/session.py`.
- Session/domain config: Extend `app/core/session.py` and `app/api/schemas.py`.
- Frontend lifecycle state: Extend `frontend/src/stores/session.ts`.
- Wizard UI: Extend `frontend/src/components/wizard/*` and `frontend/src/pages/WizardPage.tsx`.

**New Frame Or Annotation Behavior:**
- Backend frame logic: Use `app/api/routes/frames.py`.
- Backend annotation CRUD/autosave: Use `app/api/routes/annotations.py`.
- Shared annotation state: Use `app/api/state.py`.
- Frontend annotation state: Use `frontend/src/stores/annotation.ts`.
- Canvas interaction: Use `frontend/src/components/canvas/AnnotationCanvas.tsx`.

**New Export Format:**
- Export job/request contract: Extend `app/api/schemas.py` and `app/core/exporter.py`.
- Export route orchestration: Extend `app/api/routes/export.py`.
- Dataset writer implementation: Add standard bbox writers under `app/annotation/infrastructure/export/`; add OBB writers under `app/annotation_obb/infrastructure/export/`.
- Compatibility facade: Export reusable functions from `app/dataset_export.py` when scripts should call them.
- Frontend UI: Extend `frontend/src/components/modals/ExportModal.tsx`.
- Tests: Add export coverage under `tests/test_dataset_export.py` or a new focused test file.

**New Frontend Page:**
- Page component: Add `frontend/src/pages/<Name>Page.tsx`.
- Navigation/shell integration: Update `frontend/src/App.tsx` and relevant layout components under `frontend/src/components/layout/`.
- API calls: Add store actions in `frontend/src/stores/*` or API types in `frontend/src/api/types.ts`; avoid component-local ad hoc fetches for shared state.

**New Frontend Component:**
- Layout/shared app chrome: `frontend/src/components/layout/`.
- Annotation canvas tooling: `frontend/src/components/canvas/`.
- Wizard steps: `frontend/src/components/wizard/`.
- Dialogs: `frontend/src/components/modals/`.
- Shared UI context: `frontend/src/ui/`.

**New Domain Service:**
- API-independent backend behavior: `app/core/` or `app/sources/`.
- Annotation-specific domain helpers: `app/annotation/core/`.
- OBB-specific geometry/domain helpers: `app/annotation_obb/geometry/` or `app/annotation_obb/*`.
- Tracking behavior: `app/tracking/` for app wrappers, `tracker/` for tracker implementation internals.

**New CLI Utility:**
- Standalone script: `utils/<verb>_<object>.py`.
- Reuse app services from `app/dataset_export.py`, `app/sources/discovery.py`, or `app/annotation/infrastructure/export/*`.
- Add tests under `tests/` for reusable behavior instead of testing only CLI argument parsing.

**Legacy Tkinter Code:**
- Standard bbox mixins: `app/annotation/detection/`, `app/annotation/state/`, `app/annotation/sources/`, `app/annotation/roi/`.
- OBB mixins: `app/annotation_obb/detection/`, `app/annotation_obb/state/`, `app/annotation_obb/sources/`.
- Classification helpers: `app/classification/` and `app/classification/tools/`.
- Preserve the `app.api` import boundary; do not import Tkinter modules from `app/api/main.py` or route modules except lazy desktop picker functions in `app/api/routes/browse.py`.

## Special Directories

**`APLICATIVO/`:**
- Purpose: Packaged application output containing executable bundle internals.
- Generated: Yes.
- Committed: Present in workspace; `.gitignore` treats build/distribution outputs as generated.

**`build/`:**
- Purpose: Build output.
- Generated: Yes.
- Committed: Present in workspace; ignored by `.gitignore`.

**`dist/`:**
- Purpose: Distribution output.
- Generated: Yes.
- Committed: Present in workspace; ignored by `.gitignore`.

**`frontend/dist/`:**
- Purpose: Built Vite frontend mounted by `app/api/main.py` when present.
- Generated: Yes.
- Committed: Ignored by `.gitignore`.

**`frontend/src-tauri/target/`:**
- Purpose: Rust/Tauri build artifacts.
- Generated: Yes.
- Committed: Ignored by `.gitignore`.

**`output/`, `outputs/`, `output_dataset/`:**
- Purpose: Runtime annotation/export output locations.
- Generated: Yes.
- Committed: Ignored by `.gitignore` for `outputs/` and `output_dataset/`; `output/` is present in workspace.

**`saved_data_states/`:**
- Purpose: Runtime saved annotation/session state location.
- Generated: Yes.
- Committed: Ignored by `.gitignore`.

**`.planning/codebase/`:**
- Purpose: GSD codebase maps consumed by planning/execution workflows.
- Generated: Yes.
- Committed: Intended planning artifact directory.

**`.pytest_cache/`, `__pycache__/`:**
- Purpose: Python test/interpreter caches.
- Generated: Yes.
- Committed: Ignored by `.gitignore`.

**`frontend/node_modules/`:**
- Purpose: Node dependencies.
- Generated: Yes.
- Committed: Ignored by `.gitignore`.

---

*Structure analysis: 2026-06-08*
