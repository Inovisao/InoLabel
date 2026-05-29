# Codebase Structure

**Analysis Date:** 2026-05-29

## Directory Layout

```text
InoLabel/
├── main.py                    # Desktop launcher: starts FastAPI and pywebview
├── build.py                   # Frontend/PyInstaller/dev-server build helper
├── InoLabel.spec              # PyInstaller bundle specification
├── requirements.txt           # Python runtime dependencies
├── README.md                  # User setup, modes, output, and utility docs
├── assets/                    # Packaged static desktop assets
├── backend/                   # FastAPI app and Python domain/runtime code
├── frontend/                  # Vite React application
├── tests/                     # Pytest suite for backend/domain behavior
├── utils/                     # Root command-line dataset utilities
├── tracker/                   # Legacy/top-level ByteTrack implementation copy
├── outputs/                   # Generated annotation/classification outputs
├── .planning/codebase/        # Generated GSD codebase maps
├── .local/                    # Local runtime data/cache directory
└── .pytest_cache/             # Generated pytest cache
```

## Directory Purposes

**`backend/`:**
- Purpose: Python backend application, API transport layer, annotation services, tracking, export, and shared domain models.
- Contains: FastAPI entry point, routers, core session/output-state code, annotation workflow packages, classification workflow, tracking wrappers, utilities.
- Key files: `backend/main.py`, `backend/config.py`, `backend/models.py`, `backend/core/session.py`, `backend/services/session_manager.py`.

**`backend/api/`:**
- Purpose: HTTP and WebSocket boundary for frontend and desktop clients.
- Contains: One router per API area plus WebSocket broadcaster.
- Key files: `backend/api/session.py`, `backend/api/frame.py`, `backend/api/export.py`, `backend/api/wizard.py`, `backend/api/ws.py`.

**`backend/services/`:**
- Purpose: Service facades that do not fit a single router and are directly exposed by the API layer.
- Contains: Active-session singleton and classification service facade.
- Key files: `backend/services/session_manager.py`, `backend/services/classification_service.py`.

**`backend/core/`:**
- Purpose: Shared backend domain primitives and state discovery.
- Contains: Session mode/config dataclasses, output-state discovery/loading, startup cache helpers.
- Key files: `backend/core/session.py`, `backend/core/output_state.py`, `backend/core/startup_cache.py`.

**`backend/annotation/`:**
- Purpose: Standard tracking/detection annotation runtime.
- Contains: Mixin-composed tool, shared imports, lifecycle, core services, detection workflow, export/persistence infrastructure, ROI, sources, state, display helpers, keybinds.
- Key files: `backend/annotation/tool.py`, `backend/annotation/shared.py`, `backend/annotation/state/core_init.py`, `backend/annotation/detection/frame_pipeline.py`, `backend/annotation/detection/workflow_actions.py`, `backend/annotation/application/lifecycle.py`.

**`backend/annotation/core/`:**
- Purpose: Reusable domain services inside the standard annotation workflow.
- Contains: Class service, augmentation service/types, export split and YOLO label helpers.
- Key files: `backend/annotation/core/services/class_service.py`, `backend/annotation/core/augmentation/augmentation_service.py`, `backend/annotation/core/export/split_service.py`, `backend/annotation/core/export/yolo_label_service.py`.

**`backend/annotation/infrastructure/`:**
- Purpose: Filesystem persistence and export adapters for the standard annotation workflow.
- Contains: COCO storage, export actions, COCO exporter, YOLO exporter.
- Key files: `backend/annotation/infrastructure/persistence/coco_storage.py`, `backend/annotation/infrastructure/persistence/export_actions.py`, `backend/annotation/infrastructure/export/coco_exporter.py`, `backend/annotation/infrastructure/export/yolo_exporter.py`.

**`backend/annotation_obb/`:**
- Purpose: Oriented bounding box annotation runtime parallel to the standard annotation workflow.
- Contains: OBB tool composition, OBB detection workflow, OBB geometry helpers, OBB persistence/export, OBB source/state/display modules.
- Key files: `backend/annotation_obb/tool.py`, `backend/annotation_obb/geometry/obb_geometry.py`, `backend/annotation_obb/detection/frame_pipeline.py`, `backend/annotation_obb/infrastructure/export/yolo_obb_exporter.py`.

**`backend/classification/`:**
- Purpose: Image classification dataset workflow.
- Contains: Dataset discovery/copy/export functions and classification state mixin.
- Key files: `backend/classification/dataset.py`, `backend/classification/tools/state.py`.

**`backend/tracker/`:**
- Purpose: BYTETracker implementation used by backend tracking flows.
- Contains: Track base classes, Kalman filter, matching utilities, ByteTrack update logic.
- Key files: `backend/tracker/byte_tracker.py`, `backend/tracker/kalman_filter.py`, `backend/tracker/matching.py`, `backend/tracker/basetrack.py`.

**`backend/tracking/`:**
- Purpose: Higher-level tracking adapters around ByteTrack.
- Contains: Per-class tracker wrapper.
- Key files: `backend/tracking/multiclass_byte_tracking.py`.

**`backend/sources/`:**
- Purpose: Source-discovery service separate from the annotation mixin source modules.
- Contains: Source summary dataclass and discovery service.
- Key files: `backend/sources/discovery.py`.

**`backend/utils/`:**
- Purpose: Backend package copies of dataset utility scripts.
- Contains: COCO-to-YOLO conversion, tracking-to-detection conversion, augmentation, split merging.
- Key files: `backend/utils/convert_coco_to_yolo_dataset.py`, `backend/utils/convert_coco_tracking_to_detection.py`, `backend/utils/augment_output_dataset.py`, `backend/utils/merge_yolo_splits.py`.

**`frontend/`:**
- Purpose: Browser/webview client built with Vite, React, TypeScript, Tailwind, and Zustand.
- Contains: Package manifests, Vite/TS/ESLint config, public assets, React source tree.
- Key files: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/main.tsx`, `frontend/src/App.tsx`.

**`frontend/src/components/`:**
- Purpose: React UI grouped by feature area.
- Contains: Canvas overlays/workspace, export dialogs/help, layout shell, setup wizard steps.
- Key files: `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/components/layout/AppLayout.tsx`, `frontend/src/components/wizard/WizardShell.tsx`, `frontend/src/components/export/ExportDialog.tsx`.

**`frontend/src/hooks/`:**
- Purpose: Client-side integration hooks.
- Contains: WebSocket state sync and keyboard shortcut handling.
- Key files: `frontend/src/hooks/useWebSocket.ts`, `frontend/src/hooks/useKeyboard.ts`.

**`frontend/src/stores/`:**
- Purpose: Zustand stores for frontend state.
- Contains: Wizard/session state, annotation snapshot state, UI flag state.
- Key files: `frontend/src/stores/sessionStore.ts`, `frontend/src/stores/annotationStore.ts`, `frontend/src/stores/uiStore.ts`.

**`frontend/src/lib/`:**
- Purpose: Frontend shared client utilities and contracts.
- Contains: Axios API facade, TypeScript DTOs, class-name helper.
- Key files: `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, `frontend/src/lib/utils.ts`.

**`tests/`:**
- Purpose: Backend/domain pytest coverage.
- Contains: Unit tests for session config, output state, dataset export, class handling, startup cache, OBB geometry/export, keybinds.
- Key files: `tests/test_session_config.py`, `tests/test_output_state.py`, `tests/test_dataset_export.py`, `tests/test_yolo_obb_export.py`, `tests/test_classification_dataset.py`.

**`utils/`:**
- Purpose: Root-level command-line utilities documented in `README.md`.
- Contains: COCO/YOLO conversion, tracking-to-detection conversion, output dataset augmentation, YOLO split merging.
- Key files: `utils/convert_coco_to_yolo_dataset.py`, `utils/convert_coco_tracking_to_detection.py`, `utils/augment_output_dataset.py`, `utils/merge_yolo_splits.py`.

**`tracker/`:**
- Purpose: Top-level ByteTrack code copy.
- Contains: Base track, byte tracker, Kalman filter, matching utilities.
- Key files: `tracker/byte_tracker.py`, `tracker/kalman_filter.py`, `tracker/matching.py`, `tracker/basetrack.py`.

**`outputs/`:**
- Purpose: Generated annotation/classification work products.
- Contains: Per-run output directories with images, COCO annotations, YOLO exports, classification state, homography files.
- Key files: Generated only; code reads/writes through `backend/core/output_state.py`, `backend/annotation/application/lifecycle.py`, and `backend/classification/dataset.py`.

## Key File Locations

**Entry Points:**
- `main.py`: Desktop entry point; starts backend and opens pywebview.
- `backend/main.py`: FastAPI application entry point.
- `frontend/src/main.tsx`: React DOM mount.
- `frontend/src/App.tsx`: Top-level wizard-vs-workspace switch.
- `build.py`: Build and development orchestration.
- `InoLabel.spec`: PyInstaller packaging entry.

**Configuration:**
- `requirements.txt`: Python dependencies.
- `frontend/package.json`: Frontend dependencies and scripts.
- `frontend/vite.config.ts`: Vite plugins, `@` alias, `/api` and `/ws` dev proxies.
- `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`: TypeScript configuration.
- `frontend/eslint.config.js`: Frontend lint configuration.
- `backend/config.py`: Backend path, output, model, threshold, display, and behavior constants.

**Core Logic:**
- `backend/core/session.py`: Session modes and immutable session configuration.
- `backend/core/output_state.py`: Output-state discovery, resume metadata, output directory creation.
- `backend/models.py`: Detection and tracker argument dataclasses.
- `backend/services/session_manager.py`: Active runtime singleton and tool factory.
- `backend/services/classification_service.py`: Classification workflow facade.
- `backend/annotation/tool.py`: Standard annotation tool composition.
- `backend/annotation_obb/tool.py`: OBB annotation tool composition.
- `backend/annotation/detection/frame_pipeline.py`: Standard frame loading, model inference, and tracking pipeline.
- `backend/annotation/detection/workflow_actions.py`: Standard accept/reject/delete/rotation workflow actions.
- `backend/annotation/application/lifecycle.py`: Autosave and shutdown behavior.
- `backend/annotation_obb/geometry/obb_geometry.py`: OBB data model and geometry helpers.
- `backend/tracking/multiclass_byte_tracking.py`: Per-class tracking wrapper.

**API Layer:**
- `backend/api/session.py`: `/api/session` lifecycle endpoints.
- `backend/api/frame.py`: `/api/frame` action endpoints.
- `backend/api/export.py`: `/api/export` endpoint.
- `backend/api/wizard.py`: `/api/wizard` setup endpoints.
- `backend/api/ws.py`: `/ws` WebSocket endpoint.

**Frontend Integration:**
- `frontend/src/lib/api.ts`: HTTP client facade.
- `frontend/src/lib/types.ts`: Frontend DTOs and workflow unions.
- `frontend/src/hooks/useWebSocket.ts`: Realtime state sync.
- `frontend/src/hooks/useKeyboard.ts`: Keyboard command integration.
- `frontend/src/stores/sessionStore.ts`: Wizard/session state.
- `frontend/src/stores/annotationStore.ts`: Backend annotation snapshot.
- `frontend/src/stores/uiStore.ts`: UI-only mode/dialog state.

**Frontend UI:**
- `frontend/src/components/wizard/WizardShell.tsx`: Wizard container.
- `frontend/src/components/wizard/StepMode.tsx`: Mode selection.
- `frontend/src/components/wizard/StepDataset.tsx`: Dataset path selection.
- `frontend/src/components/wizard/StepOutput.tsx`: Output/resume selection.
- `frontend/src/components/wizard/StepModel.tsx`: Model/classes/session start step.
- `frontend/src/components/layout/AppLayout.tsx`: Annotation workspace shell.
- `frontend/src/components/layout/Topbar.tsx`: Top bar controls.
- `frontend/src/components/layout/Sidebar.tsx`: Annotation controls.
- `frontend/src/components/layout/Statusbar.tsx`: Status display.
- `frontend/src/components/canvas/AnnotationCanvas.tsx`: Frame display and mouse interactions.
- `frontend/src/components/canvas/BboxOverlay.tsx`: Detection overlay renderer.
- `frontend/src/components/canvas/ROIOverlay.tsx`: ROI overlay renderer.
- `frontend/src/components/export/ExportDialog.tsx`: Export modal.
- `frontend/src/components/export/KeybindHelp.tsx`: Shortcut help modal.

**Testing:**
- `tests/test_session_config.py`: Session configuration tests.
- `tests/test_output_state.py`: Output-state discovery/loading tests.
- `tests/test_startup_cache.py`: Startup cache tests.
- `tests/test_dataset_export.py`: Dataset export tests.
- `tests/test_yolo_obb_export.py`: YOLO OBB export tests.
- `tests/test_classification_dataset.py`: Classification dataset tests.
- `tests/test_keybinds.py`: Keybind behavior tests.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`: `backend/core/output_state.py`, `backend/annotation/detection/frame_pipeline.py`.
- React components use `PascalCase.tsx`: `frontend/src/components/layout/AppLayout.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`.
- React hooks use `use*.ts`: `frontend/src/hooks/useWebSocket.ts`, `frontend/src/hooks/useKeyboard.ts`.
- Zustand stores use `*Store.ts`: `frontend/src/stores/sessionStore.ts`, `frontend/src/stores/annotationStore.ts`.
- Tests use `test_*.py`: `tests/test_session_config.py`, `tests/test_obb_geometry.py`.
- Build/config files keep tool-native names: `frontend/vite.config.ts`, `frontend/eslint.config.js`, `InoLabel.spec`.

**Directories:**
- Backend feature directories use lowercase `snake_case` where needed: `backend/annotation_obb`, `backend/classification`.
- Backend annotation subdirectories group by concern: `application`, `core`, `detection`, `infrastructure`, `roi`, `sources`, `state`, `ui`.
- Frontend component subdirectories group by UI area: `canvas`, `export`, `layout`, `ui`, `wizard`.
- Generated output directories live under `outputs/` and are created by `backend/core/output_state.py`.

**Classes and Types:**
- Python classes use `PascalCase`: `SessionManager`, `AnnotationSessionConfig`, `ClassificationService`, `AnnotationTool`.
- Python mixins end in `Mixin`: `FramePipelineMixin`, `WorkflowActionsMixin`, `CocoStorageMixin`.
- TypeScript interfaces use `PascalCase`: `AnnotationState`, `StartSessionRequest`, `OutputStateInfo`.
- TypeScript type unions use `PascalCase` names with string literals: `AnnotationMode`, `CanvasMode`.

**Functions:**
- Python functions and methods use `snake_case`: `create_new_output_dir()`, `get_state_snapshot()`, `run_model()`.
- React components use `PascalCase` functions: `AppLayout()`, `AnnotationCanvas()`.
- React hooks use `useCamelCase`: `useWebSocket()`, `useKeyboard()`.

## Where to Add New Code

**New FastAPI Endpoint:**
- Primary code: Add a router function to the relevant file under `backend/api/`.
- Shared request/response models: Define local Pydantic models in the same router file unless reused across routers.
- Frontend client: Add a typed method to `frontend/src/lib/api.ts`.
- Frontend types: Add DTOs to `frontend/src/lib/types.ts`.
- Tests: Add pytest coverage under `tests/` for backend behavior and, when practical, isolate domain logic outside the router.

**New Session Mode:**
- Primary code: Add enum value and label to `backend/core/session.py`.
- Backend runtime: Add a service/tool implementation under a mode-specific `backend/` package or `backend/services/`.
- Tool selection: Extend `SessionManager._build_tool()` in `backend/services/session_manager.py`.
- Wizard/frontend contract: Update `frontend/src/lib/types.ts`, wizard screens under `frontend/src/components/wizard/`, and API client behavior in `frontend/src/lib/api.ts` if needed.
- Tests: Add coverage in `tests/test_session_config.py` and mode-specific domain tests.

**New Standard Detection Behavior:**
- Primary code: Add focused mixin behavior under `backend/annotation/detection/`, `backend/annotation/roi/`, `backend/annotation/sources/`, or `backend/annotation/state/` based on responsibility.
- Tool composition: Add the mixin to `backend/annotation/tool.py` when it needs to become part of `AnnotationTool`.
- API access: Expose through `backend/api/frame.py` only after the tool owns the operation.
- Frontend controls: Add UI under `frontend/src/components/layout/` or `frontend/src/components/canvas/` and route calls through `frontend/src/lib/api.ts`.

**New OBB Behavior:**
- Primary code: Add OBB-specific logic under `backend/annotation_obb/`.
- Geometry: Put shape math in `backend/annotation_obb/geometry/obb_geometry.py`.
- Tool composition: Add mixins to `backend/annotation_obb/tool.py`.
- Export: Add OBB output logic under `backend/annotation_obb/infrastructure/export/`.
- Tests: Add geometry/export coverage under `tests/`, following `tests/test_obb_geometry.py` and `tests/test_yolo_obb_export.py`.

**New Classification Behavior:**
- Primary code: Add dataset/state functions to `backend/classification/dataset.py` or service methods to `backend/services/classification_service.py`.
- State helper code: Add tool-specific state methods under `backend/classification/tools/`.
- API access: Expose through existing routers when it is part of session/frame/export flow, or add a new router under `backend/api/` for distinct classification endpoints.
- Tests: Add classification coverage under `tests/`, following `tests/test_classification_dataset.py`.

**New Export Format:**
- Standard annotation export: Add exporter code under `backend/annotation/infrastructure/export/` and dispatch from `backend/annotation/infrastructure/persistence/export_actions.py`.
- OBB export: Add exporter code under `backend/annotation_obb/infrastructure/export/` and dispatch from `backend/annotation_obb/infrastructure/persistence/export_actions.py`.
- API parameters: Extend `ExportRequest` in `backend/api/export.py` and `api.export.run()` in `frontend/src/lib/api.ts`.
- Tests: Add exporter tests under `tests/`.

**New Frontend Component:**
- Workspace UI: Place layout/control components under `frontend/src/components/layout/`.
- Canvas UI: Place frame/overlay interaction components under `frontend/src/components/canvas/`.
- Wizard UI: Place setup steps under `frontend/src/components/wizard/`.
- Export/help UI: Place modal/export components under `frontend/src/components/export/`.
- Shared UI primitives: Place generic primitives under `frontend/src/components/ui/`.

**New Frontend State:**
- Backend session snapshot: Extend `frontend/src/stores/annotationStore.ts` and `frontend/src/lib/types.ts`.
- Wizard setup state: Extend `frontend/src/stores/sessionStore.ts`.
- UI-only flags and modes: Extend `frontend/src/stores/uiStore.ts`.

**New Utility Script:**
- Importable backend utility: Add under `backend/utils/`.
- User-facing command utility: Add under root `utils/` and document invocation in `README.md`.
- Shared implementation: Prefer one canonical implementation and keep wrapper scripts thin if both locations are needed.

**New Tests:**
- Backend/domain tests: Add under `tests/test_*.py`.
- API tests: Use focused tests around router/domain contracts; keep filesystem output isolated with temporary directories.
- Frontend tests: Not detected in current tree; introduce only with a chosen test runner and config in `frontend/package.json`.

## Special Directories

**`.planning/codebase/`:**
- Purpose: GSD-generated codebase maps consumed by planning and execution workflows.
- Generated: Yes.
- Committed: Intended to be committed by the orchestrator.

**`outputs/`:**
- Purpose: Runtime annotation/classification outputs.
- Generated: Yes.
- Committed: Repository currently contains output directories; treat new contents as generated user data unless explicitly requested.

**`.local/`:**
- Purpose: Local runtime data/cache.
- Generated: Yes.
- Committed: Not intended for source changes.

**`.pytest_cache/`:**
- Purpose: Pytest execution cache.
- Generated: Yes.
- Committed: No.

**`frontend/dist/`:**
- Purpose: Production frontend build served by `backend/main.py` and bundled by `InoLabel.spec`.
- Generated: Yes.
- Committed: Not present in scanned file list; generated by `npm run build` through `build.py`.

**`frontend/node_modules/`:**
- Purpose: Installed frontend dependencies.
- Generated: Yes.
- Committed: No.

**`assets/`:**
- Purpose: Packaged assets such as the Inovisao logo used by `backend/config.py` and `InoLabel.spec`.
- Generated: No.
- Committed: Yes.

---

*Structure analysis: 2026-05-29*
