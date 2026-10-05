# Coding Conventions

**Analysis Date:** 2026-06-08

## Naming Patterns

**Files:**
- Python source files use lowercase snake_case modules: `app/api/routes/session.py`, `app/core/output_state.py`, `app/annotation/core/export/split_service.py`.
- Python package directories group by domain and layer: `app/api/routes/`, `app/annotation/core/`, `app/annotation/infrastructure/`, `app/annotation_obb/geometry/`.
- Python tests use `tests/test_*.py` for pytest discovery: `tests/test_api_contract.py`, `tests/test_session_start_audit.py`, `tests/test_export_improvements.py`.
- Frontend React components and pages use PascalCase filenames: `frontend/src/App.tsx`, `frontend/src/pages/WizardPage.tsx`, `frontend/src/components/modals/ExportModal.tsx`.
- Frontend stores, hooks, and API helpers use camelCase or lowercase filenames: `frontend/src/stores/session.ts`, `frontend/src/hooks/useKeyboardShortcuts.ts`, `frontend/src/api/client.ts`.
- Demo accessibility tests use `.test.js`: `.impeccable/demo/tests/accessibility.test.js`.

**Functions:**
- Python functions and methods use snake_case: `_count_frames` in `app/api/routes/session.py`, `normalize_class_names` in `app/core/session.py`, `export_yolo_dataset` in `app/dataset_export.py`.
- Private Python helpers use leading underscores: `_invalid` and `_path_type` in `app/api/routes/validation.py`, `_build_state` and `_parse_mode` in `app/core/output_state.py`.
- FastAPI route handlers are named for the endpoint action: `start_session`, `get_status`, `run_action`, and `stop_session` in `app/api/routes/session.py`.
- React component functions use PascalCase default exports: `Topbar` in `frontend/src/components/layout/Topbar.tsx`, `ExportModal` in `frontend/src/components/modals/ExportModal.tsx`.
- Frontend event handlers use `handle*` names when scoped to a component: `handleNavigate` and `handleResume` in `frontend/src/App.tsx`, `handleExport` in `frontend/src/components/modals/ExportModal.tsx`.
- Zustand actions use imperative verbs: `start`, `stop`, and `recover` in `frontend/src/stores/session.ts`.

**Variables:**
- Python constants use UPPER_SNAKE_CASE: `IMAGE_EXTENSIONS` in `app/config.py`, `FRONTEND_DIST` in `app/api/main.py`, `AUGMENTATION_CATALOG` in `app/annotation/core/augmentation/augmentation_types.py`.
- Python local variables use snake_case: `data_path`, `output_path`, `model_path`, and `total` in `app/api/routes/session.py`.
- Frontend constants use UPPER_SNAKE_CASE for module-level lookup data: `WIZARD_STEPS` in `frontend/src/App.tsx`, `MODE_LABELS` in `frontend/src/components/layout/Topbar.tsx`, `FORMATS` in `frontend/src/components/modals/ExportModal.tsx`.
- Frontend state variables use camelCase: `wizardInitial` in `frontend/src/App.tsx`, `exportState` and `errorMsg` in `frontend/src/components/modals/ExportModal.tsx`.

**Types:**
- Python dataclasses use PascalCase nouns: `AnnotationSessionConfig` in `app/core/session.py`, `StartupCache` in `app/core/startup_cache.py`, `Detection` in `app/models.py`.
- Python enums use PascalCase class names and UPPER_SNAKE_CASE members: `AnnotationTaskMode.TRACKING` in `app/core/session.py`, `TaskMode.CLASSIFICATION` in `app/api/schemas.py`.
- Pydantic request/response models use suffixes that describe API direction: `SessionStartRequest`, `SessionStartResponse`, `AnnotationUpsert` in `app/api/schemas.py`.
- TypeScript interfaces and union types use PascalCase: `SessionState` in `frontend/src/stores/session.ts`, `Props` in `frontend/src/components/layout/Topbar.tsx`, `ExportFormat` and `ExportState` in `frontend/src/components/modals/ExportModal.tsx`.

## Code Style

**Formatting:**
- Python source is formatted with 4-space indentation, blank lines between top-level definitions, and mostly Black-compatible spacing. No formatter configuration file is present at repo root.
- Python imports use one import per source group and are commonly ordered as future imports, standard library, third-party packages, then local `app.*` imports. Use this order when adding code to `app/api/routes/session.py`, `app/api/schemas.py`, or `tests/test_api_contract.py`.
- TypeScript/TSX uses 2-space indentation in JSX blocks, double quotes, semicolons, and inline style objects for most UI layout in `frontend/src/components/layout/Topbar.tsx` and `frontend/src/components/modals/ExportModal.tsx`.
- Frontend build type checking is configured through `frontend/tsconfig.json` with `strict: true`, `noEmit: true`, `jsx: react-jsx`, and `moduleResolution: bundler`.
- No root `.prettierrc`, `.eslintrc`, `eslint.config.*`, `pyproject.toml`, `pytest.ini`, `ruff.toml`, or `mypy.ini` is detected.

**Linting:**
- No active linter command or config is detected for Python.
- Existing Python files contain compatibility comments for pylint broad exception handling, such as `# pylint: disable=broad-except` in `app/annotation/application/lifecycle.py` and `app/annotation/core/services/class_service.py`; keep these only where broad exception handling is intentionally non-fatal.
- The frontend includes inline ESLint suppression for React hook dependency behavior in `frontend/src/App.tsx`; there is no installed eslint dependency or script in `frontend/package.json`.
- TypeScript compile checking is the effective frontend static check. Use `npm run build` from `frontend/` to run `tsc && vite build`.

## Import Organization

**Order:**
1. Future imports, when present: `from __future__ import annotations` in `app/api/main.py`, `app/api/routes/session.py`, `app/core/session.py`.
2. Python standard library imports: `json`, `logging`, `datetime`, `pathlib` in `app/api/routes/session.py`.
3. Third-party imports: `fastapi`, `pydantic`, `cv2`, `numpy`, `ultralytics` in files such as `app/api/routes/session.py`, `app/api/schemas.py`, and `tests/main_test.py`.
4. Local application imports: `from app.api.schemas import ...` in `app/api/routes/session.py`, `from app.config import ...` in `app/api/routes/validation.py`.
5. TypeScript value imports before type-only imports when both are used: `frontend/src/App.tsx` imports React hooks and pages first, then `import type { WizardState } ...`.

**Path Aliases:**
- Python code uses absolute package imports rooted at `app`, `tracker`, and `utils`: `from app.api.state import active_session`, `from utils.merge_yolo_splits import merge_yolo_splits`.
- Frontend code uses relative imports from `frontend/src`; no TypeScript path alias is configured in `frontend/tsconfig.json`.
- API imports must not pull Tkinter UI modules. `tests/test_api_contract.py` asserts that importing `app.api.main` does not load `tkinter` or `app.ui`.

## Error Handling

**Patterns:**
- FastAPI endpoints raise `HTTPException` for hard request failures and return response models on success. Use this pattern in route files under `app/api/routes/`, as in `start_session` and `run_action` in `app/api/routes/session.py`.
- API validation endpoints can return structured 422 JSON responses instead of exceptions when the response body includes a domain-specific validity object. Use `_invalid()` in `app/api/routes/validation.py` as the local pattern.
- Pydantic validators enforce request normalization and domain constraints in `app/api/schemas.py`. Add schema-level input cleanup with `@model_validator(mode="after")` and field range checks with `@field_validator`.
- Domain/core modules raise standard Python exceptions (`ValueError`, `FileNotFoundError`, `RuntimeError`) rather than HTTP exceptions. Examples: `app/core/session.py`, `app/core/output_state.py`, `app/annotation/infrastructure/export/yolo_exporter.py`.
- Non-critical persistence failures are swallowed only when the feature can degrade safely. `app/api/routes/session.py` ignores metadata write `OSError`; `app/api/routes/validation.py` skips unreadable project metadata.
- Frontend API failures are converted to `Error` in `frontend/src/api/client.ts` and stored in component/store state in `frontend/src/stores/session.ts` and `frontend/src/components/modals/ExportModal.tsx`.

## Logging

**Framework:** Python `logging` for API/server flows; `print` for Tkinter/CLI runtime flows; no frontend logging framework detected.

**Patterns:**
- Use `logging.getLogger(__name__)` in API route modules that need operational logs. `app/api/routes/session.py` logs session replacement and creation.
- Use `print("[INFO] ...")`, `print("[AVISO] ...")`, and `print("[ERRO] ...")` in Tkinter-facing annotation flows where messages surface to local runtime output, as in `app/annotation/application/lifecycle.py`, `app/annotation/detection/workflow_actions.py`, and `app/annotation/roi/roi_state.py`.
- Avoid `console.log` in frontend application code; no `console.*` calls are detected in `frontend/src`.
- Demo tests log their own lifecycle and failures directly in `.impeccable/demo/tests/accessibility.test.js`.

## Comments

**When to Comment:**
- Use docstrings for modules, API routes, dataclasses, and helpers that encode workflow or business invariants. Examples: `app/api/main.py`, `app/api/routes/session.py`, `app/core/session.py`, `tests/test_session_start_audit.py`.
- Use short inline comments for sequencing constraints and compatibility behavior, especially where state mutation order matters. `app/api/routes/session.py` labels the validate/stop/create sequence; `app/api/schemas.py` documents class deduplication order.
- Avoid decorative section dividers in new Python code unless extending files that already use them. Several existing legacy/runtime files use large divider comments in `app/annotation/core/services/class_service.py` and `tests/test_session_start_audit.py`.

**JSDoc/TSDoc:**
- Not detected in frontend source. Use TypeScript type aliases/interfaces and readable names instead of adding JSDoc by default.
- Python docstrings are preferred over type comments for public helpers and dataclasses.

## Function Design

**Size:** 
- Prefer small pure helpers for reusable transformations: `normalize_class_names` in `app/core/session.py`, `normalize_split_ratios` in `app/annotation/core/export/split_service.py`, `_path_type` in `app/api/routes/validation.py`.
- Route handlers may be larger when they coordinate validation, state transitions, and response construction. Keep side-effect ordering explicit like `start_session` in `app/api/routes/session.py`.
- Legacy mixin methods in annotation runtime are larger and stateful. When changing `app/annotation/*`, keep edits narrowly scoped and prefer moving pure calculations into `app/annotation/core/`.

**Parameters:** 
- Use keyword-only parameters for optional behavior toggles when ambiguity is likely, such as `set_active_class(self, class_name: str, *, apply_to_selection: bool = True)` in `app/annotation/core/services/class_service.py`.
- Use `Path` for filesystem inputs inside Python code. Convert external string inputs at the API boundary, as in `app/api/routes/session.py` and `app/api/routes/validation.py`.
- Use typed request/response objects for FastAPI endpoints in `app/api/schemas.py` rather than ad hoc dictionaries for new public API bodies.

**Return Values:** 
- Core helpers return concrete typed values (`Tuple[str, ...]`, `Optional[Path]`, `dict[str, float]`) and raise for invalid inputs.
- API endpoints return Pydantic response models or JSON-compatible dictionaries.
- Frontend async store actions return `Promise<void>` and update store state rather than returning UI payloads directly, as in `frontend/src/stores/session.ts`.

## Module Design

**Exports:** 
- Python modules expose functions, dataclasses, and mixin classes directly; no `__all__` convention is detected.
- Route modules expose `router = APIRouter(...)` and are registered centrally in `app/api/main.py`.
- Frontend component files default-export one primary component. Shared helpers use named exports, such as `api` in `frontend/src/api/client.ts` and `useSessionStore` in `frontend/src/stores/session.ts`.

**Barrel Files:** 
- Python package `__init__.py` files are mostly lightweight. Some compatibility lazy exports are implemented through `__getattr__` in `app/annotation/__init__.py` and `app/annotation_obb/__init__.py`.
- Frontend does not use barrel index files; import components and stores from their concrete paths.

---

*Convention analysis: 2026-06-08*
