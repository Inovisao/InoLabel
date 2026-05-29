# Codebase Concerns

**Analysis Date:** 2026-05-29

## Tech Debt

**Frontend/backend coordinate contract is inconsistent:**
- Issue: The React canvas sends normalized coordinates in the `0..1` range while backend frame endpoints and detection/storage logic use pixel coordinates. `BboxOverlay` and `ROIOverlay` also multiply backend values by rendered image dimensions, so pixel bboxes from model inference render far outside the image while manual frontend bboxes persist as tiny pixel values.
- Files: `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/components/canvas/BboxOverlay.tsx`, `frontend/src/components/canvas/ROIOverlay.tsx`, `frontend/src/lib/types.ts`, `backend/api/frame.py`, `backend/annotation/detection/frame_pipeline.py`, `backend/annotation/infrastructure/persistence/coco_storage.py`
- Impact: Manual annotations, ROI points, selection, display overlays, and exported COCO/YOLO boxes can disagree about units. This can silently corrupt annotations even when the UI appears usable.
- Fix approach: Define one coordinate contract in `frontend/src/lib/types.ts` and `backend/models.py`. Prefer backend API payloads in image pixels with explicit `frame_width`/`frame_height` in state, or normalize all backend detection serialization/export ingestion consistently. Add route tests that submit manual boxes and assert exported COCO values.

**Detection, OBB, and classification modes share UI/API surfaces without mode-specific contracts:**
- Issue: `Sidebar` and `useKeyboard` call generic `/api/frame/*` endpoints for all active sessions, but `ClassificationService` exposes `classify`, `skip`, `previous`, and `undo` methods rather than `on_accept`/`on_reject`. No classification API route or frontend class-selection action calls `ClassificationService.classify`.
- Files: `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/hooks/useKeyboard.ts`, `frontend/src/lib/api.ts`, `backend/api/frame.py`, `backend/services/classification_service.py`
- Impact: Classification mode can start, render an image, and export state, but the primary workflow cannot classify images through the current frontend/API path. Generic frame actions can return 500 errors for classification sessions.
- Fix approach: Add `backend/api/classification.py` or mode-aware endpoints in `backend/api/frame.py` for `classify`, `skip`, `previous`, and `undo`. Hide detection-only canvas controls for classification and route number/class clicks to classification actions.

**Duplicated top-level modules create drift risk:**
- Issue: Tracker files exist both under `tracker/` and `backend/tracker/`; several utility files exist both under `utils/` and `backend/utils/`. Tracker pairs are exact copies, while `utils/augment_output_dataset.py`, `utils/convert_coco_to_yolo_dataset.py`, and `utils/convert_coco_tracking_to_detection.py` differ from their `backend/utils/` counterparts.
- Files: `tracker/byte_tracker.py`, `backend/tracker/byte_tracker.py`, `tracker/basetrack.py`, `backend/tracker/basetrack.py`, `utils/augment_output_dataset.py`, `backend/utils/augment_output_dataset.py`, `utils/convert_coco_to_yolo_dataset.py`, `backend/utils/convert_coco_to_yolo_dataset.py`, `utils/convert_coco_tracking_to_detection.py`, `backend/utils/convert_coco_tracking_to_detection.py`
- Impact: Bug fixes and behavior changes can land in only one copy. CLI utilities and backend imports can diverge without tests detecting it.
- Fix approach: Keep implementation in one package path, preferably `backend/`, and turn top-level `utils/*.py` into thin CLI wrappers importing backend functions. Remove or vendor-lock top-level `tracker/` if `backend/tracker/` is the canonical import path.

**Large legacy-style script and broad mixin composition are hard to modify safely:**
- Issue: `utils/annotation_tool_bytetracked.py` is over 1,000 lines and duplicates concepts now split across backend mixins. Core tools are assembled via many mixins and dynamic `hasattr` checks instead of explicit interfaces.
- Files: `utils/annotation_tool_bytetracked.py`, `backend/annotation/tool.py`, `backend/annotation_obb/tool.py`, `backend/api/export.py`, `backend/api/frame.py`, `backend/services/session_manager.py`
- Impact: Adding a mode or changing a workflow requires knowing implicit method names across mixins. Missing methods fail at runtime, as seen with classification and OBB differences.
- Fix approach: Introduce explicit protocol classes for session tools, detection tools, exportable tools, and classification tools. Keep `utils/annotation_tool_bytetracked.py` as archived/reference code or remove it from the supported path after confirming no build/runtime dependency.

**Python dependency and tooling configuration is under-specified:**
- Issue: `requirements.txt` contains unpinned packages and there is no detected `pyproject.toml`, `pytest.ini`, `ruff.toml`, `mypy.ini`, or coverage configuration.
- Files: `requirements.txt`, `frontend/package.json`, `frontend/package-lock.json`
- Impact: Python installs can change behavior across machines, especially `ultralytics`, `opencv-python`, `numpy`, `scipy`, `lapx`, `fastapi`, and `uvicorn`. Python lint/type/test settings are not centrally enforced.
- Fix approach: Add pinned or bounded Python dependencies and a `pyproject.toml` containing pytest, ruff, and optional mypy settings. Keep `frontend/package-lock.json` as the frontend dependency source of truth.

## Known Bugs

**ROI endpoint does not compute homography:**
- Symptoms: `POST /api/frame/roi` assigns `tool.roi_points` but checks for `_compute_homography`, while the mixin method is named `compute_homography`. Frontend ROI points are also normalized fractions, but backend homography code expects pixel coordinates.
- Files: `backend/api/frame.py`, `backend/annotation/roi/roi_state.py`, `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/components/canvas/ROIOverlay.tsx`
- Trigger: Select four ROI points in the React canvas.
- Workaround: Not detected in the React workflow. Backend-side code path `ROIStateMixin.add_roi_point` computes homography, but the frontend does not call it.

**WebSocket URL breaks on `127.0.0.1` Vite dev origin:**
- Symptoms: `useWebSocket` connects to port `7432` only when `window.location.hostname === 'localhost'`; on `127.0.0.1:5173` it uses port `5173`, which is the Vite server, not the FastAPI server.
- Files: `frontend/src/hooks/useWebSocket.ts`, `frontend/vite.config.ts`, `main.py`
- Trigger: Open the frontend through `http://127.0.0.1:5173` during development.
- Workaround: Use `http://localhost:5173` during development, or derive the WebSocket URL from Vite proxy/current origin consistently.

**OBB export leaves stale files in the export directory:**
- Symptoms: `export_yolo_obb_dataset` creates `output_dir/images/train` and `output_dir/labels/train` but does not clear an existing `output_dir`, unlike standard YOLO export which removes `dataset_root` first.
- Files: `backend/annotation_obb/infrastructure/export/yolo_obb_exporter.py`, `backend/annotation_obb/infrastructure/persistence/export_actions.py`, `backend/annotation/infrastructure/export/yolo_exporter.py`
- Trigger: Export OBB dataset after deleting annotations or reducing the source image set.
- Workaround: Manually delete `outputs/.../yolo_obb_dataset` before exporting OBB again.

**Frontend action failures are swallowed:**
- Symptoms: `Sidebar`, `AnnotationCanvas`, and `useKeyboard` catch API errors and ignore them, so backend 400/500 responses do not surface in the UI.
- Files: `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/hooks/useKeyboard.ts`, `frontend/src/lib/api.ts`
- Trigger: Any backend failure from frame actions, export path errors, missing classification method, invalid ROI, or invalid detection index.
- Workaround: Browser devtools show failed network requests; the app UI does not expose the error.

## Security Considerations

**Unauthenticated local API can mutate files and session state:**
- Risk: FastAPI and WebSocket endpoints have no authentication, CSRF token, or WebSocket origin validation. The desktop entry point binds to `127.0.0.1`, but development and direct `uvicorn` usage can still expose filesystem-affecting operations to local browser contexts.
- Files: `main.py`, `backend/main.py`, `backend/api/session.py`, `backend/api/frame.py`, `backend/api/export.py`, `backend/api/wizard.py`, `backend/api/ws.py`
- Current mitigation: `main.py` binds the desktop server to `127.0.0.1`; CORS allows only `http://localhost:5173` and `http://127.0.0.1:5173`.
- Recommendations: Keep the server loopback-only by default, reject unexpected WebSocket `Origin` headers, add a per-process random token passed to the frontend, and require it on state-mutating routes.

**Annotation `file_name` values can escape output/export roots:**
- Risk: File paths from loaded COCO state are used directly in joins such as `self.output_images_dir / file_name`, `source_images_dir / file_name`, and `dataset_root / "images" / split / file_name`. Absolute paths or `..` segments in a malicious annotation file can target files outside the intended output or export directory.
- Files: `backend/annotation/infrastructure/persistence/coco_storage.py`, `backend/annotation_obb/infrastructure/persistence/obb_coco_storage.py`, `backend/annotation/infrastructure/export/yolo_exporter.py`, `backend/annotation_obb/infrastructure/export/yolo_obb_exporter.py`, `backend/core/output_state.py`, `backend/api/wizard.py`
- Current mitigation: Newly generated image names from `build_output_file_name` are normally relative names derived from the selected data root.
- Recommendations: Add a `safe_relative_image_path()` helper that rejects absolute paths, drive roots, empty paths, and `..` parts before any read, write, copy, or unlink. Use resolved containment checks before unlinking or writing files.

**Arbitrary filesystem path validation and native dialogs are exposed as routes:**
- Risk: `/api/wizard/validate-path`, `/api/wizard/browse-folder`, and `/api/wizard/browse-file` expose local filesystem probing and native dialog opening to any client accepted by the API server.
- Files: `backend/api/wizard.py`, `frontend/src/components/wizard/StepDataset.tsx`, `frontend/src/lib/api.ts`
- Current mitigation: Intended use is a local desktop app.
- Recommendations: Gate these routes behind the same local session token as state-mutating routes and keep them disabled or loopback-only in any hosted mode.

## Performance Bottlenecks

**Recursive dataset discovery is synchronous and unbounded:**
- Problem: Source discovery uses `Path.rglob("*")` over user-selected directories for videos, images, and image lists. Classification discovery also scans recursively.
- Files: `backend/annotation/sources/source_discovery.py`, `backend/classification/dataset.py`, `backend/services/classification_service.py`, `backend/api/session.py`
- Cause: Startup work runs inside request handling and performs full directory walks before the session is ready.
- Improvement path: Move discovery to a background task with progress reporting, cap or page very large scans, and allow explicit file lists to bypass full tree traversal.

**Frame state serialization re-encodes JPEGs for every state response and broadcast:**
- Problem: `SessionManager.get_state()` calls `get_frame_b64()`, which renders overlays and encodes a JPEG. It is used by REST responses and WebSocket broadcasts after actions.
- Files: `backend/services/session_manager.py`, `backend/annotation/tool.py`, `backend/annotation_obb/tool.py`, `backend/api/frame.py`, `backend/api/ws.py`
- Cause: State and image payload are coupled into one JSON response.
- Improvement path: Separate metadata state from frame image transport. Cache rendered frame bytes by frame/action revision or serve frames through a dedicated image endpoint.

**COCO state is rewritten as a full JSON document on every accept/autosave:**
- Problem: `write_annotations()` serializes complete `images` and `annotations` lists each time. Export also reloads and reconciles full JSON state.
- Files: `backend/annotation/infrastructure/persistence/coco_storage.py`, `backend/annotation_obb/infrastructure/persistence/obb_coco_storage.py`, `backend/annotation/infrastructure/persistence/export_actions.py`
- Cause: The state model is an in-memory COCO payload persisted as a monolithic file.
- Improvement path: Keep current COCO export format, but persist working state incrementally in a lightweight database or append journal for large projects, then materialize COCO on export.

**Review cache stores full frame copies in memory:**
- Problem: `saved_records` keeps copied frame arrays and optional rectified frames with `MAX_SAVED_FRAME_CACHE = 200`.
- Files: `backend/config.py`, `backend/annotation/detection/review_nav.py`, `backend/annotation_obb/detection/review_nav.py`
- Cause: Review mode caches image arrays rather than paths plus serialized detections.
- Improvement path: Store record metadata and reload images from `output_images_dir` on demand, or scale cache size by estimated frame memory.

## Fragile Areas

**Global mutable session singleton:**
- Files: `backend/services/session_manager.py`, `backend/api/frame.py`, `backend/api/export.py`, `backend/api/session.py`, `backend/api/ws.py`
- Why fragile: Only `start()` and `stop()` hold a lock. Frame routes, WebSocket actions, export, render, and notification callbacks mutate the same tool object without serialization.
- Safe modification: Funnel tool mutations through one session operation queue or protect all tool access with a re-entrant lock. Add tests for concurrent REST/WebSocket actions before changing session lifecycle.
- Test coverage: Existing tests cover pure functions and some mixin behavior, but no FastAPI concurrency or WebSocket tests are detected.

**Broad exception handling hides failures:**
- Files: `backend/services/session_manager.py`, `backend/api/ws.py`, `backend/annotation/application/lifecycle.py`, `backend/annotation/sources/source_loading.py`, `backend/annotation_obb/infrastructure/persistence/export_actions.py`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/hooks/useKeyboard.ts`
- Why fragile: Many `except Exception` blocks log to stdout, set a generic message, or silently `pass`. The caller often cannot distinguish recoverable conditions from data loss or stale state.
- Safe modification: Replace silent catches with typed exceptions at module boundaries and user-visible errors in the frontend. Keep broad catches only around cleanup paths, and log structured context.
- Test coverage: No tests assert frontend error display, WebSocket error behavior, or lifecycle cleanup failures.

**OBB implementation is behaviorally divergent from standard detection:**
- Files: `backend/annotation_obb/tool.py`, `backend/annotation_obb/detection/workflow_actions.py`, `backend/annotation_obb/detection/review_nav.py`, `backend/annotation_obb/infrastructure/persistence/export_actions.py`, `backend/annotation/tool.py`, `backend/annotation/detection/workflow_actions.py`, `backend/annotation/detection/review_nav.py`, `backend/annotation/infrastructure/persistence/export_actions.py`
- Why fragile: OBB mode reimplements review, deletion, export, and state serialization with different feature coverage. Examples include no `sync_export_metadata`, no video previous-frame support, and a fixed `yolo_obb_dataset` export target.
- Safe modification: Extract shared review/delete/export orchestration and keep only geometry-specific detection serialization in OBB modules.
- Test coverage: `tests/test_obb_geometry.py` and `tests/test_yolo_obb_export.py` cover geometry/export formatting, but route-level OBB workflow tests are not detected.

## Scaling Limits

**Single active session per process:**
- Current capacity: One `session_manager.tool` per Python process.
- Limit: Multiple annotation jobs, users, or browser tabs share one mutable session and can overwrite each other.
- Scaling path: Introduce session IDs and per-session tool instances, or explicitly enforce a single-client desktop contract with a token and UI lock.

**Large datasets keep all annotation metadata in process memory:**
- Current capacity: The app stores `images`, `annotations`, detection lists, review records, and classification records in Python lists.
- Limit: Large COCO files and long annotation sessions increase memory use and full-file save time.
- Scaling path: Persist working state incrementally and load only current/review-window records into memory.

**Export operations are full rebuilds:**
- Current capacity: YOLO and COCO exports copy/rewrite complete datasets.
- Limit: Re-exporting after small changes is proportional to total saved images and can block the app.
- Scaling path: Add incremental export metadata or run exports in a background worker with cancellable progress.

## Dependencies at Risk

**Unpinned Python ML/vision stack:**
- Risk: `requirements.txt` has no version bounds for `ultralytics`, `opencv-python`, `Pillow`, `numpy`, `scipy`, `lapx`, `fastapi`, `uvicorn[standard]`, `websockets`, `python-multipart`, or `pywebview`.
- Impact: Install reproducibility and PyInstaller builds can break when upstream packages change APIs or binary wheels.
- Migration plan: Generate a pinned lock file for the supported Python version and platform, then keep `requirements.txt` as human-readable direct dependencies with compatible upper bounds.

**Vendored BYTETracker copy has no local dependency boundary:**
- Risk: BYTETracker code is copied into both `tracker/` and `backend/tracker/`.
- Impact: Security, license, and algorithm bug fixes require manual synchronization.
- Migration plan: Keep one vendored location with a source/version note and remove duplicate import paths.

**Frontend dependency versions are modern and tightly coupled to lockfile:**
- Risk: `frontend/package.json` uses React 19, TypeScript 6, Vite 8, ESLint 10, and Tailwind 4 ranges while the lockfile pins the actual install.
- Impact: Removing or regenerating `frontend/package-lock.json` can pull a different toolchain than the current app was tested with.
- Migration plan: Treat `frontend/package-lock.json` as required and run `npm ci` in CI/build scripts.

## Missing Critical Features

**Classification annotation controls:**
- Problem: The backend classification service has state and export logic, but the API/frontend do not expose class assignment actions.
- Blocks: Completing the advertised classification workflow from the React UI.
- Files: `backend/services/classification_service.py`, `backend/api/frame.py`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`

**End-to-end route and UI validation:**
- Problem: Python unit tests cover exporters, state helpers, class mapping, and geometry, but not running FastAPI routes, WebSocket flows, browser canvas interactions, or the packaged desktop entry point.
- Blocks: Detecting coordinate-contract regressions, classification route gaps, WebSocket URL failures, and CORS/auth behavior before release.
- Files: `tests/test_dataset_export.py`, `tests/test_session_config.py`, `tests/test_yolo_obb_export.py`, `backend/api/frame.py`, `backend/api/ws.py`, `frontend/src/components/canvas/AnnotationCanvas.tsx`

**Centralized Python quality gate:**
- Problem: No Python lint, type, coverage, or pytest configuration file is detected.
- Blocks: Enforcing conventions across backend mixins, APIs, and utilities.
- Files: `requirements.txt`, `backend/`, `utils/`, `tests/`

## Test Coverage Gaps

**Coordinate conversion and ROI API:**
- What's not tested: Frontend-to-backend bbox units, ROI point units, `POST /api/frame/roi`, manual detection save/export roundtrip.
- Files: `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/components/canvas/BboxOverlay.tsx`, `backend/api/frame.py`, `backend/annotation/roi/roi_state.py`, `backend/annotation/infrastructure/persistence/coco_storage.py`
- Risk: Annotation corruption can ship without failing unit tests.
- Priority: High

**Classification workflow through API/UI:**
- What's not tested: Starting a classification session, classifying an image from the UI, skipping/undoing, and exporting classified records through HTTP.
- Files: `backend/services/classification_service.py`, `backend/api/frame.py`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/hooks/useKeyboard.ts`
- Risk: A supported mode remains non-functional from the app surface.
- Priority: High

**Security/path traversal behavior:**
- What's not tested: Malicious `file_name` values in loaded COCO state, absolute paths, `..` segments, delete/export containment, and WebSocket origin handling.
- Files: `backend/annotation/infrastructure/persistence/coco_storage.py`, `backend/annotation_obb/infrastructure/persistence/obb_coco_storage.py`, `backend/annotation/infrastructure/export/yolo_exporter.py`, `backend/api/ws.py`
- Risk: Local files can be read, overwritten, copied, or deleted outside intended roots if untrusted annotation files are loaded.
- Priority: High

**FastAPI and WebSocket integration:**
- What's not tested: Route status codes, error payloads, broadcast consistency, concurrent actions, CORS settings, and frontend WebSocket URL variants.
- Files: `backend/main.py`, `backend/api/session.py`, `backend/api/frame.py`, `backend/api/export.py`, `backend/api/ws.py`, `frontend/src/hooks/useWebSocket.ts`
- Risk: Regressions appear only during manual desktop/browser testing.
- Priority: Medium

**Frontend components and stores:**
- What's not tested: Wizard flow, export dialog behavior, canvas drawing/selection/ROI, keyboard shortcuts, error display, and Zustand store transitions.
- Files: `frontend/src/components/wizard/`, `frontend/src/components/export/ExportDialog.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/stores/annotationStore.ts`, `frontend/src/stores/sessionStore.ts`
- Risk: UI regressions and broken workflows are not caught by automated tests.
- Priority: Medium

---

*Concerns audit: 2026-05-29*
