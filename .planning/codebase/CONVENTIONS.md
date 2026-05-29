# Coding Conventions

**Analysis Date:** 2026-05-29

## Naming Patterns

**Files:**
- Use `snake_case.py` for Python modules, including API routers, services, and core helpers: `backend/api/session.py`, `backend/core/output_state.py`, `backend/services/session_manager.py`.
- Use `test_*.py` for Python test modules under `tests/`: `tests/test_session_config.py`, `tests/test_dataset_export.py`, `tests/test_obb_geometry.py`.
- Use `PascalCase.tsx` for React components: `frontend/src/components/wizard/WizardShell.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`.
- Use `camelCase.ts` for frontend hooks, stores, and utility modules: `frontend/src/hooks/useWebSocket.ts`, `frontend/src/stores/sessionStore.ts`, `frontend/src/lib/api.ts`.
- Use package `__init__.py` files for Python package boundaries: `backend/api/__init__.py`, `backend/annotation/__init__.py`, `backend/annotation_obb/__init__.py`.

**Functions:**
- Python functions and methods use `snake_case`: `normalize_class_names` in `backend/core/session.py`, `create_new_output_dir` in `backend/core/output_state.py`, `sanitize_class_dir_name` in `backend/classification/dataset.py`.
- Private Python helpers use a leading underscore: `_require_tool` in `backend/api/frame.py`, `_build_tool` in `backend/services/session_manager.py`, `_find_dist` in `backend/main.py`.
- FastAPI endpoint handlers are short verb phrases matching the route behavior: `start_session` in `backend/api/session.py`, `accept_frame` in `backend/api/frame.py`, `run_export` in `backend/api/export.py`.
- React components use PascalCase exported functions: `AppLayout` in `frontend/src/components/layout/AppLayout.tsx`, `StepDataset` in `frontend/src/components/wizard/StepDataset.tsx`.
- React hooks use the `use*` prefix: `useWebSocket` in `frontend/src/hooks/useWebSocket.ts`, `useKeyboard` in `frontend/src/hooks/useKeyboard.ts`.
- Zustand stores use `use*Store`: `useSessionStore` in `frontend/src/stores/sessionStore.ts`, `useAnnotationStore` in `frontend/src/stores/annotationStore.ts`, `useUIStore` in `frontend/src/stores/uiStore.ts`.

**Variables:**
- Python constants use uppercase at module scope: `STATE_FILE_NAME` and `STATE_PATTERN` in `backend/classification/dataset.py`, `_HOST` and `_PORT` in `main.py`.
- Python local variables use descriptive `snake_case`: `source_images_dir`, `dataset_root`, and `annotations_path` in `tests/test_dataset_export.py` and `backend/api/session.py`.
- TypeScript state setters use `set*` names and state values use compact camelCase: `setWizardData`, `setWizardStep`, and `wizardData` in `frontend/src/stores/sessionStore.ts`.
- TypeScript refs use `*Ref` suffixes: `wsRef` in `frontend/src/hooks/useWebSocket.ts`, `containerRef` and `imgRef` in `frontend/src/components/canvas/AnnotationCanvas.tsx`.

**Types:**
- Python dataclasses use PascalCase nouns: `AnnotationSessionConfig` in `backend/core/session.py`, `Detection` and `ByteTrackerArgs` in `backend/models.py`, `ClassificationRecord` in `backend/classification/dataset.py`.
- Python enums use PascalCase class names with uppercase members: `AnnotationTaskMode.TRACKING`, `AnnotationTaskMode.DETECTION`, and `AnnotationTaskMode.CLASSIFICATION` in `backend/core/session.py`.
- Pydantic request models use PascalCase with a `Request` suffix: `StartSessionRequest` in `backend/api/session.py`, `ManualDetectionRequest` and `ROIRequest` in `backend/api/frame.py`.
- TypeScript interfaces use PascalCase nouns: `AnnotationState`, `Detection`, `WizardMode`, and `StartSessionRequest` in `frontend/src/lib/types.ts`.
- TypeScript discriminated string unions are used for constrained values: `AnnotationMode` in `frontend/src/lib/types.ts`, `phase: 'wizard' | 'annotating'` in `frontend/src/stores/sessionStore.ts`.

## Code Style

**Formatting:**
- Python uses 4-space indentation, explicit `Path` conversion, and standard library imports before third-party imports before local imports: `backend/classification/dataset.py`, `backend/core/session.py`, `tests/test_dataset_export.py`.
- Python modules commonly start with `from __future__ import annotations` when modern typing is used: `main.py`, `backend/main.py`, `backend/core/session.py`, `backend/dataset_export.py`.
- Python code does not have a detected formatter configuration file; no `pyproject.toml`, `setup.cfg`, `.flake8`, or `.prettierrc` is present for Python formatting.
- TypeScript/React uses 2-space indentation, single quotes, no semicolons, and concise arrow callbacks: `frontend/src/lib/api.ts`, `frontend/src/stores/sessionStore.ts`, `frontend/src/components/layout/AppLayout.tsx`.
- Frontend styling is inline Tailwind utility classes in `className` strings: `frontend/src/components/wizard/StepDataset.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`.
- The shared `cn` helper wraps `clsx` and `tailwind-merge`; use it when composing conditional class strings that need merging: `frontend/src/lib/utils.ts`.

**Linting:**
- Frontend linting is configured with ESLint flat config in `frontend/eslint.config.js`.
- ESLint applies `@eslint/js` recommended rules, `typescript-eslint` recommended rules, `eslint-plugin-react-hooks`, and `eslint-plugin-react-refresh` to `**/*.{ts,tsx}`: `frontend/eslint.config.js`.
- TypeScript compiler checks unused locals, unused parameters, fallthrough switch cases, and bundler module resolution: `frontend/tsconfig.app.json`.
- Frontend lint command is `npm run lint` from `frontend/package.json`.
- Python linting is not configured in repository files. Use the existing code style in `backend/` and `tests/` instead of introducing new lint-only rewrites.

## Import Organization

**Order:**
1. Python future imports when present, followed by standard library imports: `backend/core/session.py`, `backend/classification/dataset.py`.
2. Third-party imports after standard library imports: `numpy`, `cv2`, `fastapi`, and `pydantic` in `backend/api/frame.py` and `tests/test_dataset_export.py`.
3. Local imports last, using absolute `backend.*` imports for application modules: `backend/api/session.py`, `backend/api/frame.py`, `tests/test_session_config.py`.
4. TypeScript imports external packages first, then alias imports, then relative imports: `frontend/src/components/wizard/StepDataset.tsx`, `frontend/src/components/layout/AppLayout.tsx`.
5. Type-only imports use `import type`: `frontend/src/lib/api.ts`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/stores/sessionStore.ts`.

**Path Aliases:**
- Frontend uses `@/*` for `frontend/src/*`, configured in `frontend/vite.config.ts` and `frontend/tsconfig.app.json`.
- Use alias imports for cross-folder frontend code: `@/stores/sessionStore` in `frontend/src/App.tsx`, `@/lib/api` in `frontend/src/components/wizard/StepDataset.tsx`.
- Use relative imports for sibling component files: `./WizardNav` in `frontend/src/components/wizard/StepDataset.tsx`, `./BboxOverlay` in `frontend/src/components/canvas/AnnotationCanvas.tsx`.
- Python code uses absolute package imports from `backend` for application modules: `backend.services.session_manager` in `backend/api/session.py`, `backend.models` in `backend/api/frame.py`.

## Error Handling

**Patterns:**
- API input validation raises `HTTPException` with 400-level status for user-correctable request problems: `_require_tool` and ROI validation in `backend/api/frame.py`, invalid session mode in `backend/api/session.py`, missing classification `output_dir` in `backend/api/export.py`.
- API operation failures are caught and returned as `HTTPException(500, str(exc))`: `start_session` in `backend/api/session.py`, `accept_frame` in `backend/api/frame.py`, `run_export` in `backend/api/export.py`.
- Domain helpers raise `ValueError` or `FileNotFoundError` for invalid state and missing files: `AnnotationSessionConfig.__post_init__` in `backend/core/session.py`, `load_required_state` in `backend/classification/dataset.py`, `merge_yolo_splits` in `utils/merge_yolo_splits.py`.
- State-listing helpers skip corrupt or incompatible files by catching narrow exceptions: `list_output_states` in `backend/classification/dataset.py`.
- Runtime cleanup and notification callbacks intentionally suppress best-effort failures: `SessionManager.start`, `SessionManager.stop`, and `notify_frame_update` in `backend/services/session_manager.py`.
- Frontend API errors are normalized in an Axios response interceptor before rejection: `frontend/src/lib/api.ts`.
- Frontend UI actions commonly set local error state for user-facing validation failures and ignore cancelled dialogs: `validate`, `browse`, and `importCoco` in `frontend/src/components/wizard/StepDataset.tsx`.
- WebSocket message parsing ignores malformed messages and reconnects after close: `frontend/src/hooks/useWebSocket.ts`.

## Logging

**Framework:** `logging` for the FastAPI app; `print` for desktop entry points and CLI utilities.

**Patterns:**
- Configure backend logging once at application startup: `logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")` in `backend/main.py`.
- Use module loggers for async infrastructure: `logger = logging.getLogger(__name__)` in `backend/api/ws.py`.
- Use bracketed Portuguese status prefixes for command-line tools: `[OK]`, `[INFO]`, `[AVISO]`, and `[ERRO]` in `build.py`, `utils/merge_yolo_splits.py`, and `utils/convert_coco_to_yolo_dataset.py`.
- Avoid adding browser `console.*` logging in frontend components; no `console.log` pattern is present under `frontend/src`.

## Comments

**When to Comment:**
- Use module docstrings to describe module purpose: `backend/main.py`, `backend/api/session.py`, `backend/classification/dataset.py`.
- Use short docstrings for public helpers, dataclasses, and endpoint handlers: `normalize_class_names` in `backend/core/session.py`, `sanitize_class_dir_name` in `backend/classification/dataset.py`, `accept_frame` in `backend/api/frame.py`.
- Use comments to mark major sections in API and UI files when files group many handlers or operations: `backend/api/frame.py`, `backend/api/session.py`, `frontend/src/lib/api.ts`.
- Use comments for non-obvious compatibility or fallback behavior: PyInstaller handling in `backend/main.py`, legacy fallback note in `source_looks_used` in `backend/classification/dataset.py`.
- Keep frontend comments near coordinate conversion, drawing state, and SVG overlay logic where geometry is easy to misread: `frontend/src/components/canvas/AnnotationCanvas.tsx`.

**JSDoc/TSDoc:**
- JSDoc/TSDoc is not detected in frontend modules. Prefer readable TypeScript interfaces in `frontend/src/lib/types.ts` and small helper names over adding broad documentation blocks.

## Function Design

**Size:** Keep new functions small for API glue and pure helpers. Endpoint wrappers in `backend/api/frame.py` and `backend/api/session.py` validate, call the session tool, and return state. Larger domain modules such as `backend/classification/dataset.py` are split into many focused helpers instead of one orchestration function.

**Parameters:** Prefer keyword-only parameters for domain functions with multiple related values: `export_classification_dataset`, `transfer_image_to_class`, and `write_state` in `backend/classification/dataset.py`. Use Pydantic request models for FastAPI request bodies: `StartSessionRequest` in `backend/api/session.py`, `EditDetectionRequest` in `backend/api/frame.py`.

**Return Values:** Return plain dataclasses for internal structured state, dictionaries for API/export reports, and `Path | None` or object `| None` for optional discovery results: `ClassificationOutputState` in `backend/classification/dataset.py`, `export_yolo_dataset` in `backend/dataset_export.py`, `find_state_path` in `backend/classification/dataset.py`.

## Module Design

**Exports:** Python modules expose direct functions, dataclasses, and mixin classes through module imports rather than explicit `__all__`: `backend/classification/dataset.py`, `backend/models.py`, `backend/annotation/detection/workflow_actions.py`.

**Barrel Files:** Python package `__init__.py` files are present but do not act as rich barrel exports in the inspected files: `backend/__init__.py`, `backend/api/__init__.py`, `backend/services/__init__.py`.

**State Boundaries:**
- Keep global mutable runtime state centralized in the singleton `session_manager` from `backend/services/session_manager.py`.
- Keep frontend session state in Zustand stores, not component-level globals: `frontend/src/stores/sessionStore.ts`, `frontend/src/stores/annotationStore.ts`, `frontend/src/stores/uiStore.ts`.
- Keep API transport code in `frontend/src/lib/api.ts`; components should call `api.*` methods rather than creating their own Axios clients.

**Where to Put New Quality-Aligned Code:**
- New backend API route: add a focused router module under `backend/api/` and include it in `backend/main.py`.
- New backend domain helper: add it beside the owning feature under `backend/core/`, `backend/classification/`, `backend/annotation/`, or `backend/annotation_obb/`.
- New frontend component: add a PascalCase component under the relevant `frontend/src/components/<area>/` directory.
- New frontend shared type: add to `frontend/src/lib/types.ts` when it represents API/state shape shared by multiple modules.
- New frontend server call: add to the grouped `api` object in `frontend/src/lib/api.ts`.

---

*Convention analysis: 2026-05-29*
