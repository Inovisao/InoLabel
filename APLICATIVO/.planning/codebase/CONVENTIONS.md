---
last_mapped_commit: af6f39f6d52b32e68a7d38ed4a1b747fd1283f01
---
# Coding Conventions

**Analysis Date:** 2026-06-02

## Naming Patterns

**Files:**
- Use snake_case for Python modules: `app/core/session.py`, `app/annotation/core/services/class_service.py`, `app/annotation/infrastructure/export/yolo_exporter.py`.
- Use package `__init__.py` files to expose Python package boundaries: `app/__init__.py`, `app/annotation/__init__.py`, `app/annotation/core/export/__init__.py`.
- Use PascalCase for React component files: `frontend/src/components/wizard/Wizard.tsx`, `frontend/src/pages/AnnotatePage.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`.
- Use camelCase for frontend non-component modules: `frontend/src/hooks/useKeyboardShortcuts.ts`, `frontend/src/api/client.ts`, `frontend/src/stores/session.ts`.
- Use `test_*.py` for Python tests in `tests/`: `tests/test_session_config.py`, `tests/test_dataset_export.py`, `tests/test_tracker_matching_fallbacks.py`.

**Functions:**
- Use snake_case for Python functions and methods: `normalize_class_names` in `app/core/session.py`, `export_yolo_dataset` in `app/annotation/infrastructure/export/yolo_exporter.py`, `_tk_sequence` in `app/annotation/keybinds/keybind_service.py`.
- Prefix implementation-only Python helpers with `_`: `_write_yolo_box_file` in `app/annotation/infrastructure/export/yolo_exporter.py`, `_bbox_overlaps_numpy` in `tracker/matching.py`, `_parse_event_key` in `app/annotation/keybinds/keybind_editor.py`.
- Use verb-led names for UI actions and side effects: `apply_target_classes`, `autosave_classes`, `remove_class` in `app/annotation/core/services/class_service.py`.
- Use camelCase for TypeScript functions, component locals, and Zustand actions: `fetchFrame`, `nextFrame`, `setSelectedClass` in `frontend/src/stores/annotation.ts`.
- Use `use*` names for React hooks and Zustand stores: `useSessionStore` in `frontend/src/stores/session.ts`, `useAnnotationStore` in `frontend/src/stores/annotation.ts`, `useKeyboardShortcuts` in `frontend/src/hooks/useKeyboardShortcuts.ts`.

**Variables:**
- Use snake_case in Python: `session_config` in `app/runner.py`, `source_images_dir` and `dataset_root` in `tests/test_dataset_export.py`.
- Use UPPER_SNAKE_CASE for Python module constants: `CONF_THRESHOLD`, `DATA_ROOT`, `IMAGE_EXTENSIONS` in `app/config.py`; `AUGMENTATION_CATALOG` in `app/annotation/core/augmentation/augmentation_types.py`.
- Use camelCase in TypeScript: `selectedClassId`, `totalFrames`, `currentIndex` in `frontend/src/stores/session.ts` and `frontend/src/stores/annotation.ts`.
- Preserve API payload snake_case at the boundary: `total_frames`, `current_index`, `image_b64`, and `category_id` appear in `frontend/src/api/types.ts`, `frontend/src/stores/session.ts`, and `frontend/src/stores/annotation.ts`.

**Types:**
- Use PascalCase for Python classes, dataclasses, enums, and mixins: `AnnotationSessionConfig` in `app/core/session.py`, `AugmentationPreset` in `app/annotation/core/augmentation/augmentation_types.py`, `ClassServiceMixin` in `app/annotation/core/services/class_service.py`.
- Use `*Mixin` suffix for behavior slices composed into Tkinter tools: `SelectionEditMixin` in `app/annotation/detection/selection_edit.py`, `KeybindMixin` in `app/annotation/keybinds/keybind_mixin.py`, `ExportActionsMixin` in `app/annotation/infrastructure/persistence/export_actions.py`.
- Use PascalCase for Pydantic request/response schemas: `SessionStartRequest`, `SessionStatus`, `FrameResponse` in `app/api/schemas.py`.
- Use TypeScript interfaces for frontend state and payload contracts: `SessionState` in `frontend/src/stores/session.ts`, `AnnotationState` in `frontend/src/stores/annotation.ts`, `WizardState` in `frontend/src/components/wizard/Wizard.tsx`.

## Code Style

**Formatting:**
- Python has no detected formatter config: no `pyproject.toml`, `.black`, `setup.cfg`, or `tox.ini` at the repository root.
- Keep Python formatting close to the existing PEP 8 style in `app/core/session.py` and `app/annotation/infrastructure/export/yolo_exporter.py`: four-space indentation, blank lines between top-level definitions, and wrapped calls for long argument lists.
- Python type hints are used on newer core modules and should be added for new service, API, and utility code: `app/core/session.py`, `app/api/schemas.py`, `app/annotation/core/augmentation/augmentation_types.py`.
- Older or compatibility-heavy modules use looser typing and dynamic attributes; match the existing mixin style when extending those areas: `app/annotation/core/services/class_service.py`, `app/annotation/keybinds/keybind_service.py`.
- Frontend formatting is TypeScript/Vite default style with two-space indentation, double quotes, semicolons, trailing commas in multiline objects, and JSX in `.tsx`: `frontend/src/main.tsx`, `frontend/src/stores/session.ts`, `frontend/src/components/wizard/Wizard.tsx`.
- CSS uses Tailwind v4 `@theme` tokens plus class primitives in `frontend/src/styles.css`. Prefer existing CSS variables such as `--color-amber`, `--radius-md`, and `--color-surface-2`.

**Linting:**
- No active Python lint config is detected. Some files include inline `pylint` suppressions, for example `# pylint: disable=broad-except` in `app/runner.py`, `app/ui/theme/tokens.py`, and `app/annotation/keybinds/keybind_service.py`.
- No active frontend lint config is detected. `frontend/package.json` provides `dev`, `build`, `preview`, and `tauri`, but no `lint` or `test` script.
- TypeScript strictness is enforced through `frontend/tsconfig.json`: `strict: true`, `isolatedModules: true`, and `noFallthroughCasesInSwitch: true`; unused locals and parameters are not blocked.

## Import Organization

**Order:**
1. Future imports at the top when used: `from __future__ import annotations` in `app/core/session.py`, `app/annotation/infrastructure/export/yolo_exporter.py`, and `app/api/schemas.py`.
2. Python standard library imports next: `sys`, `Path`, `Enum`, `dataclass`, `typing` in `app/runner.py`, `app/core/session.py`, and `app/api/schemas.py`.
3. Third-party imports next: `cv2` in `app/annotation/infrastructure/export/yolo_exporter.py`, `numpy` in `app/models.py`, `pydantic` in `app/api/schemas.py`.
4. Local `app.*`, `tracker.*`, and `utils.*` imports last: `app.config` in `app/core/session.py`, `app.annotation.core.export.*` in `app/annotation/infrastructure/export/yolo_exporter.py`.
5. React imports come before local frontend imports: `react`, `react-dom`, `zustand`, `framer-motion`, and `react-konva` precede `./stores/session` and `../../api/types` in `frontend/src/main.tsx`, `frontend/src/stores/session.ts`, and `frontend/src/components/canvas/AnnotationCanvas.tsx`.

**Path Aliases:**
- Python uses package imports rooted at `app`, `tracker`, and `utils`: `app.core.session`, `tracker.matching`, `utils.merge_yolo_splits`.
- Frontend has no path alias configured in `frontend/tsconfig.json`; use relative imports such as `../api/client`, `../../stores/annotation`, and `./pages/WizardPage`.

## Error Handling

**Patterns:**
- Validate domain inputs by raising `ValueError` in pure/core code: `AnnotationSessionConfig.__post_init__` in `app/core/session.py`, `_normalized_split_ratios` in `app/annotation/infrastructure/export/yolo_exporter.py`, and `add_class_directory` in `app/classification/dataset.py`.
- Raise `FileNotFoundError` for missing required files during export: `export_yolo_dataset` and `export_yolo_no_split` in `app/annotation/infrastructure/export/yolo_exporter.py`.
- Return process status integers from CLI entry points and wrap with `SystemExit`: `main.py`, `app/runner.py`, `utils/merge_yolo_splits.py`, `utils/convert_coco_to_yolo_dataset.py`.
- Use broad exception handlers only at UI, lifecycle, and compatibility boundaries where the app must stay interactive: `app/runner.py`, `app/annotation/application/lifecycle.py`, `app/annotation/sources/source_loading.py`.
- Frontend API errors are normalized into thrown `Error` objects in `frontend/src/api/client.ts`; Zustand stores catch and store user-facing messages in `frontend/src/stores/session.ts`.
- For new FastAPI endpoints, use Pydantic validators and response models at `app/api/schemas.py` and route through `app/api/routes/*.py` instead of validating raw dictionaries inside route functions.

## Logging

**Framework:** console/standard output

**Patterns:**
- Python runtime code uses `print` with bracketed Portuguese severity tags such as `[INFO]`, `[AVISO]`, and `[ERRO]`: `app/annotation/core/services/class_service.py`, `app/annotation/detection/workflow_actions.py`, `app/annotation/roi/roi_state.py`.
- CLI utilities print status summaries and return non-zero on errors: `utils/merge_yolo_splits.py`, `utils/convert_coco_to_yolo_dataset.py`, `tests/main_test.py`.
- No `logging` framework setup is detected in `app/`, `tracker/`, `utils/`, or `tests/`.
- Frontend surfaces errors through store state and UI rendering, not console logging: `frontend/src/stores/session.ts`, `frontend/src/components/wizard/Wizard.tsx`.

## Comments

**When to Comment:**
- Use module docstrings for files that define a coherent subsystem or public utility: `app/core/session.py`, `app/annotation/infrastructure/export/yolo_exporter.py`, `app/ui/components/button.py`.
- Use short comments for UI/event intent and boundary behavior: resize and image-loading comments in `frontend/src/components/canvas/AnnotationCanvas.tsx`, "Special keys" comments in `app/annotation/keybinds/keybind_service.py`.
- Avoid long decorative divider comments in new code unless editing an existing file that already uses them, such as `app/annotation/core/services/class_service.py` and `app/annotation/keybinds/keybind_service.py`.

**JSDoc/TSDoc:**
- TSDoc is not used in the frontend. Type contracts live in TypeScript interfaces in `frontend/src/api/types.ts`, `frontend/src/stores/session.ts`, and `frontend/src/components/wizard/Wizard.tsx`.
- Python docstrings are used for public dataclasses, enums, helpers, and factories: `ByteTrackerArgs` in `app/models.py`, `AnnotationTaskMode` in `app/core/session.py`, `make_btn` in `app/ui/components/button.py`.

## Function Design

**Size:** Keep new pure functions focused and testable like `normalize_class_names` in `app/core/session.py`, `compute_split_counts` in `app/annotation/core/export/split_service.py`, and `_normalized_split_ratios` in `app/annotation/infrastructure/export/yolo_exporter.py`. Large UI workflows are currently decomposed into mixins rather than free functions.

**Parameters:** Prefer `Path` objects for filesystem APIs and convert at the boundary: `AnnotationSessionConfig` in `app/core/session.py`, `export_yolo_dataset` in `app/annotation/infrastructure/export/yolo_exporter.py`, and classification dataset helpers in `app/classification/dataset.py`.

**Return Values:** Return structured dictionaries for export/report functions: `export_yolo_dataset` and `export_yolo_no_split` in `app/annotation/infrastructure/export/yolo_exporter.py`, `merge_yolo_splits` in `utils/merge_yolo_splits.py`. Return dataclasses or Pydantic models for typed configuration and API data: `app/core/session.py`, `app/api/schemas.py`.

## Module Design

**Exports:** Python modules usually export named classes/functions directly and avoid explicit `__all__`: `app/core/session.py`, `app/annotation/core/augmentation/augmentation_types.py`, `app/annotation/infrastructure/export/yolo_exporter.py`.

**Barrel Files:** Python package barrels are used selectively for UI components: `app/ui/components/__init__.py` exposes factories consumed by `tests/test_components.py`. Frontend barrel files are not used; import concrete modules by relative path.

**Composition:** Tkinter annotation tools are split into mixins by responsibility, with implementation under `app/annotation/*`, `app/annotation_obb/*`, and `app/classification/tools/*`. Add behavior to the smallest matching mixin, then compose through existing tool classes such as `app/annotation/tool.py`, `app/annotation_obb/tool.py`, and `app/classification/tools/core.py`.

---

*Convention analysis: 2026-06-02*
