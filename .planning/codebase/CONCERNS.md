# Codebase Concerns

**Analysis Date:** 2026-06-08

## Tech Debt

**Process-global API state:**
- Issue: API session, export, frame, annotation, and frame-position state live in module-level mutable objects instead of request/session-scoped storage.
- Files: `app/api/state.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `app/api/routes/export.py`, `frontend/src/stores/session.ts`, `frontend/src/stores/annotation.ts`
- Impact: Multiple browser tabs, concurrent requests, or background export tasks can observe or mutate the same active session. `POST /api/export` validates `body.session_id`, but `_run_export()` reads `active_session()` instead of binding the job to that session, so a new session can redirect an export to different in-memory data.
- Fix approach: Store `session_id` on `ExportJob`, pass it into `_run_export()`, and make frame cursor, loaded-frame cache, frame paths, dimensions, annotations, and ID counters keyed by `session_id`. Keep a single-session desktop mode as a policy layer, not as implicit global data.

**Silent broad exception handling:**
- Issue: Many paths catch broad exceptions and continue with `pass`, empty lists, or logged-only failures.
- Files: `app/api/routes/annotations.py`, `app/api/routes/validation.py`, `app/annotation/sources/source_helpers.py`, `app/annotation_obb/sources/source_helpers.py`, `app/annotation/application/lifecycle.py`, `app/core/output_state.py`, `app/classification/dataset.py`
- Impact: Autosave, resume, model reset, source discovery, metadata loading, and project listing can fail without user-visible feedback. Users may believe annotations or projects are persisted when writes or reads are skipped.
- Fix approach: Replace broad `pass` blocks with narrow exception types and user-visible warnings where data is affected. Keep non-critical metadata failures non-fatal, but return structured warning fields from API routes and surface them in `frontend/src/ui/ToastContext.tsx`.

**Duplicated detection and OBB source helpers:**
- Issue: Source-loading and resume logic is duplicated across detection and OBB mixins with only small differences.
- Files: `app/annotation/sources/source_helpers.py`, `app/annotation_obb/sources/source_helpers.py`, `app/annotation/shared.py`, `app/annotation_obb/shared.py`
- Impact: Resume behavior, frame cursor handling, OpenCV setup, and source name normalization can drift between detection and OBB modes.
- Fix approach: Extract a shared source-session service that accepts mode-specific hooks for tracker reset and selected-object state. Keep mode-specific OBB geometry in `app/annotation_obb/geometry/obb_geometry.py`.

**Wildcard shared imports:**
- Issue: Core mixins import large dependency surfaces through wildcard modules.
- Files: `app/annotation/sources/source_helpers.py`, `app/annotation_obb/shared.py`, `app/annotation/shared.py`
- Impact: Dependencies such as `tkinter`, `ultralytics`, OpenCV, tracker classes, and configuration constants are available implicitly, making import boundaries fragile and increasing side-effect risk.
- Fix approach: Replace wildcard imports with explicit imports in each module. Keep API-safe lazy wrappers in `app/core/detector.py` and `app/core/tracker.py` as the boundary for heavy dependencies.

**Generated output tracked in git:**
- Issue: A generated label file is tracked under an output directory that `.gitignore` treats as generated data.
- Files: `output/labels/DJI_0727.txt`, `.gitignore`
- Impact: Local annotation data can leak into source control and make future test runs or manual sessions appear dirty.
- Fix approach: Remove generated output files from version control and keep only deterministic fixtures under `tests/fixtures/` or similar test-only paths.

## Known Bugs

**Export can use the wrong active session:**
- Symptoms: An export request for one `session_id` can export whichever session is active when the background task runs.
- Files: `app/api/routes/export.py`, `app/api/state.py`, `app/core/exporter.py`
- Trigger: Start session A, start an export, then start session B before the background export reads `active_session()`.
- Workaround: Avoid starting a new session while an export is running.

**Frame navigation is shared across all clients:**
- Symptoms: `next`, `prev`, and `goto` mutate one `_current_index` for the whole process, so another browser tab or client can move the displayed frame.
- Files: `app/api/routes/frames.py`, `frontend/src/stores/annotation.ts`
- Trigger: Open the same running backend from two tabs and navigate frames from both.
- Workaround: Use a single client tab per backend process.

**Autosave failures do not fail annotation mutations:**
- Symptoms: `POST /api/annotations/{image_id}` and delete endpoints can return success even when the label file write fails.
- Files: `app/api/routes/annotations.py`, `frontend/src/stores/annotation.ts`, `frontend/src/components/canvas/AnnotationCanvas.tsx`
- Trigger: Make `session.output_path/labels` unwritable or remove read access to the image needed for dimensions.
- Workaround: Check output label files after annotation sessions when storage permissions are uncertain.

## Security Considerations

**No authentication or authorization on local API:**
- Risk: Any process that can reach `127.0.0.1:8765` can call session, annotation, export, browse, and validation endpoints while the backend is running.
- Files: `app/api/main.py`, `api_server.py`, `main.py`, `frontend/src/api/client.ts`
- Current mitigation: Uvicorn binds to `127.0.0.1`, and CORS origins are limited to local development/Tauri origins.
- Recommendations: Add a per-process bearer token or signed local session token and require it on every `/api/*` endpoint. Keep CORS narrow and avoid adding wildcard origins.

**Filesystem paths are accepted directly from API requests:**
- Risk: Local callers can validate, count, list, start sessions from, or export to arbitrary paths accessible to the user account.
- Files: `app/api/routes/validation.py`, `app/api/routes/session.py`, `app/api/routes/export.py`, `app/api/routes/browse.py`, `frontend/src/pages/ProjectsPage.tsx`, `frontend/src/pages/HistoryPage.tsx`
- Current mitigation: Export dataset name is constrained under the requested destination by `_safe_output_path()` in `app/api/routes/export.py`.
- Recommendations: Introduce an allowlist rooted at user-selected project/output directories. Require explicit user selection before scanning or writing outside known roots, and reject path traversal through symlinks where the destination must stay inside a project root.

**Development debug endpoint exposes annotation metadata:**
- Risk: `/api/annotations/debug` returns frame indices, counts, and the next annotation ID without any guard.
- Files: `app/api/routes/annotations.py`
- Current mitigation: It returns metadata only, not raw bounding boxes.
- Recommendations: Remove the endpoint from production builds or guard it behind an explicit development flag checked in `app/config.py`.

**Native browse endpoints are GET requests with side effects:**
- Risk: Calling `/api/browse/folder` or `/api/browse/file` opens native Tk dialogs from the backend process.
- Files: `app/api/routes/browse.py`
- Current mitigation: CORS restricts browser origins to local app origins.
- Recommendations: Make browse actions `POST`, require the same local auth token as other API routes, and return a clear error when the backend is headless.

## Performance Bottlenecks

**Recursive filesystem scans on request path:**
- Problem: Path validation, session start frame counting, source discovery, and project listing use recursive or full-directory scans synchronously or in a threadpool.
- Files: `app/api/routes/validation.py`, `app/api/routes/session.py`, `app/sources/discovery.py`, `app/classification/dataset.py`, `app/core/output_state.py`
- Cause: `Path.rglob("*")`, `iterdir()`, and `stat()` are used directly against user-selected directories.
- Improvement path: Add cancellable scan jobs with progress, cache summaries by `(path, mtime)`, and set a maximum file count or traversal budget for UI-triggered validation.

**Frames are returned as base64 JPEG payloads:**
- Problem: Every frame fetch reads with OpenCV, encodes to JPEG, base64-encodes the image, and embeds it in JSON.
- Files: `app/api/routes/frames.py`, `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/stores/annotation.ts`
- Cause: The API returns `image_b64` in `FrameResponse` rather than streaming binary image data.
- Improvement path: Serve frames through a binary endpoint with cache headers and keep JSON responses for metadata/annotations only.

**Export copies all selected images through staging and then copies again:**
- Problem: API export first copies images to a temporary staging directory, then YOLO export copies staged images into the final dataset.
- Files: `app/api/routes/export.py`, `app/annotation/infrastructure/export/yolo_exporter.py`
- Cause: Duplicate file-name handling is performed by staging files before invoking exporters that require source images by final name.
- Improvement path: Let exporters accept `(source_path, export_name)` pairs, avoiding the temporary directory for large datasets.

**Linear annotation lookups scale poorly:**
- Problem: COCO storage and review code scan `self.images` and `self.annotations` lists for image and annotation lookups.
- Files: `app/annotation/infrastructure/persistence/coco_storage.py`, `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`, `app/annotation/detection/review_annotations.py`, `tests/test_annotation_storage_perf.py`
- Cause: No maintained index exists for image file name, image ID, or annotations by image ID.
- Improvement path: Maintain indexes next to the list payload and rebuild them after load/write mutations. Keep `tests/test_annotation_storage_perf.py` as behavior coverage while adding size/performance assertions.

## Fragile Areas

**Destructive export overwrite:**
- Files: `app/annotation/infrastructure/export/yolo_exporter.py`, `app/api/routes/export.py`, `tests/test_dataset_export.py`, `tests/test_export_improvements.py`
- Why fragile: `export_yolo_dataset()` and `export_yolo_no_split()` delete `dataset_root` when it exists. A wrong destination/name combination can remove an existing dataset before export validation completes.
- Safe modification: Resolve and validate the final destination before deletion, write to a temporary sibling directory, then atomically rename into place after success.
- Test coverage: Path resolution and user export roots are tested, but API-level destructive overwrite and interrupted export behavior need direct tests.

**Annotation persistence split between memory and label files:**
- Files: `app/api/routes/annotations.py`, `app/api/routes/frames.py`, `app/api/routes/export.py`
- Why fragile: The API store is authoritative for export during a running session, while autosave writes YOLO text files opportunistically. Resume loads per frame lazily only when frames are viewed.
- Safe modification: Introduce a persistence service with explicit transaction results and centralize load/save/export reads there.
- Test coverage: Session and annotation regression tests exist in `tests/test_session_start_audit.py`; autosave failure paths and lazy resume/export completeness need more coverage.

**Desktop UI and API coexistence boundaries:**
- Files: `app/annotation/shared.py`, `app/core/detector.py`, `app/core/tracker.py`, `tests/test_api_contract.py`
- Why fragile: Tests enforce that API import avoids UI modules, but the legacy shared modules still import Tkinter, YOLO, OpenCV, and tracker dependencies eagerly.
- Safe modification: Keep API route modules importing only `app/core/*` wrappers and plain data/service modules. Move Tkinter-only dependencies behind UI constructors.
- Test coverage: `tests/test_api_contract.py` covers API import boundaries; add tests for new service modules to prevent accidental heavy imports.

**Frontend state assumes immediate backend consistency:**
- Files: `frontend/src/stores/session.ts`, `frontend/src/stores/annotation.ts`, `frontend/src/components/modals/ExportModal.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`
- Why fragile: Stores optimistically update local frame annotation lists after API success but do not refetch after autosave warnings, background export errors, or class list changes.
- Safe modification: Return explicit persistence/export warning states from the API and refetch frame metadata after operations that can alter annotation state.
- Test coverage: Backend API tests exist; no frontend unit, component, or Playwright tests are detected.

## Scaling Limits

**Single active annotation session per backend:**
- Current capacity: One active session is represented by `active_session()` and one shared `annotation_store`.
- Limit: Multi-user, multi-project, or multi-tab workflows conflict in frame navigation and annotations.
- Scaling path: Key all runtime state by `session_id`, expose session-specific frame endpoints, and garbage-collect stopped/expired sessions.

**In-memory annotation and export state only:**
- Current capacity: Sessions and export jobs live in Python dictionaries for the lifetime of the uvicorn process.
- Limit: Backend restart loses active session state, export progress, and unsaved in-memory annotations.
- Scaling path: Persist session metadata, export jobs, and annotation deltas to files under each project output directory or a lightweight local SQLite database.

**Large dataset processing is local and synchronous per worker:**
- Current capacity: Recursive scans, image reads, JPEG encoding, and export copies run in the same backend process.
- Limit: Large folders can make the API slow or memory/disk intensive, and exports have no cancellation endpoint.
- Scaling path: Move long operations into cancellable job objects with progress, cancellation, and bounded worker pools.

## Dependencies at Risk

**Unpinned Python packages:**
- Risk: `requirements.txt` lists packages without versions, including `ultralytics`, `opencv-python`, `fastapi`, `uvicorn[standard]`, and `python-jose[cryptography]`.
- Impact: Fresh installs can receive incompatible major/minor releases that change model inference, OpenCV behavior, FastAPI/Pydantic validation, or packaging.
- Migration plan: Pin known-good versions in `requirements.txt` or adopt a lockfile workflow. Keep upgrade work in explicit dependency-update phases with test runs.

**No lint/format/static-analysis configuration detected:**
- Risk: There is no repo-root Python lint config and no frontend ESLint/Biome config detected.
- Impact: Broad exceptions, wildcard imports, implicit any-style frontend patterns, and dead code can enter without automated feedback.
- Migration plan: Add `ruff` or equivalent Python linting plus TypeScript/React linting. Start with non-disruptive rules for unused imports, broad exception warnings, wildcard imports, and TypeScript strictness.

**Tauri/frontend package versions use broad semver ranges:**
- Risk: `frontend/package.json` allows compatible-range updates across React 19, Tauri 2, Vite 6, Zustand 5, and Radix packages.
- Impact: UI/runtime behavior can differ across installs if `frontend/package-lock.json` is not consistently used.
- Migration plan: Treat `frontend/package-lock.json` as required for installs and CI; update dependencies in controlled batches.

## Missing Critical Features

**Export cancellation and recovery:**
- Problem: Export jobs expose progress but no cancel endpoint, no durable progress, and no cleanup guarantee for interrupted exports.
- Blocks: Users cannot safely stop long exports or recover from backend restarts.

**Frontend automated verification:**
- Problem: The frontend has build scripts but no detected unit/component/e2E test runner configuration.
- Blocks: Canvas interactions, wizard flows, export polling, project history, and modal behavior can regress without automated feedback.

**User-visible persistence health:**
- Problem: Autosave and metadata persistence failures are logged or ignored in backend code but are not represented in API response models.
- Blocks: Users cannot know whether a session is fully persisted without inspecting output files manually.

## Test Coverage Gaps

**Autosave failure semantics:**
- What's not tested: HTTP behavior when `_autosave()` cannot create labels, cannot read image dimensions, or cannot write the `.txt` file.
- Files: `app/api/routes/annotations.py`, `tests/test_session_start_audit.py`
- Risk: API success can mask data loss.
- Priority: High

**Concurrent session/export behavior:**
- What's not tested: Export started for one session while another session starts, multi-tab frame navigation, and session-specific annotation isolation.
- Files: `app/api/state.py`, `app/api/routes/frames.py`, `app/api/routes/export.py`, `tests/test_api_contract.py`
- Risk: Users can export or edit the wrong in-memory dataset.
- Priority: High

**Destructive export interruptions:**
- What's not tested: Existing dataset deletion followed by export failure, crash, or missing source image.
- Files: `app/annotation/infrastructure/export/yolo_exporter.py`, `app/api/routes/export.py`, `tests/test_dataset_export.py`, `tests/test_export_audit.py`
- Risk: Existing export output can be lost.
- Priority: High

**Frontend interaction coverage:**
- What's not tested: Drawing/removing annotations on `AnnotationCanvas`, export polling in `ExportModal`, wizard validation flows, and project/history localStorage behavior.
- Files: `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/components/modals/ExportModal.tsx`, `frontend/src/components/wizard/Wizard.tsx`, `frontend/src/pages/ProjectsPage.tsx`, `frontend/src/pages/HistoryPage.tsx`
- Risk: UI regressions reach users even when backend tests pass.
- Priority: Medium

**Filesystem security boundaries:**
- What's not tested: Rejection of symlink escapes, arbitrary output roots, debug endpoint exposure, and browse endpoint behavior in headless or unauthorized contexts.
- Files: `app/api/routes/validation.py`, `app/api/routes/session.py`, `app/api/routes/export.py`, `app/api/routes/browse.py`, `app/api/routes/annotations.py`
- Risk: Local API callers can scan or write unintended filesystem locations.
- Priority: Medium

---

*Concerns audit: 2026-06-08*
