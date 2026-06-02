---
last_mapped_commit: af6f39f6d52b32e68a7d38ed4a1b747fd1283f01
---

# Codebase Concerns

**Analysis Date:** 2026-06-02

## Tech Debt

**CI does not enforce Python test success:**
- Issue: The Python test step masks failures with `python -m pytest -q || true`.
- Files: `.github/workflows/ci.yml`, `tests/test_dataset_export.py`, `tests/test_session_installer.py`, `tests/test_classification_dataset.py`
- Impact: Pull requests can pass CI while core export, session, classification, and persistence tests fail.
- Fix approach: Remove `|| true`, split slow/optional dependency tests behind explicit markers, and make the required unit suite blocking.

**CI tests a demo app instead of the checked-in frontend:**
- Issue: The Node step runs inside `.impeccable/demo`, while the production frontend lives under `frontend/`.
- Files: `.github/workflows/ci.yml`, `frontend/package.json`, `frontend/src/App.tsx`
- Impact: TypeScript, React, Vite, and Tauri integration regressions in `frontend/` are not caught by CI.
- Fix approach: Run `npm ci` and `npm run build` in `frontend/`, then add frontend unit or browser tests before keeping demo coverage.

**Split product runtimes are not aligned:**
- Issue: The desktop runtime in `main.py` launches the Tkinter implementation through `app/runner.py`, while the Tauri runtime in `frontend/src-tauri/src/lib.rs` launches `api_server` and the React UI talks to FastAPI routes.
- Files: `main.py`, `app/runner.py`, `build.sh`, `api_server.py`, `app/api/main.py`, `frontend/src-tauri/src/lib.rs`, `frontend/src/api/client.ts`
- Impact: Features implemented in the mature Tkinter flow are not automatically available in the React/Tauri flow. Build, startup, save, export, and annotation behavior can diverge.
- Fix approach: Treat one runtime as canonical per feature. When adding React/Tauri functionality, route it through the same domain/export services used by `app/annotation/` instead of creating parallel in-memory behavior in `app/api/`.

**FastAPI backend is a prototype state layer:**
- Issue: API session, frame index, and annotation data are module-level in-memory values rather than persisted session state.
- Files: `app/api/state.py`, `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`
- Impact: Restarting the backend loses annotations, concurrent requests share a single global session, and the API does not reuse the tested persistence path in `app/annotation/infrastructure/persistence/coco_storage.py`.
- Fix approach: Back API operations with `AnnotationSessionConfig`, `CocoStorageMixin`, and output-state services from `app/core/output_state.py`; make per-session state explicit and persist annotations through the same COCO files as the Tkinter app.

**Mixin composition is large and order-sensitive:**
- Issue: `AnnotationTool` and `OBBAnnotationTool` are built from long inheritance lists with implicit method contracts between mixins.
- Files: `app/annotation/tool.py`, `app/annotation_obb/tool.py`, `app/annotation/state/core_init.py`, `app/annotation/state/runtime_state.py`
- Impact: Moving a method or adding a mixin can break runtime behavior through method-resolution-order changes or missing attributes initialized elsewhere.
- Fix approach: Keep new code inside the existing layer directories, but prefer extracting pure services for new behavior before adding another mixin. When changing mixin contracts, add tests against the composed tool contract in `tests/`.

**HBB and OBB annotation flows duplicate behavior:**
- Issue: OBB reimplements variants of source helpers, frame pipeline, workflow actions, review navigation, selection editing, persistence, and UI event handling.
- Files: `app/annotation/detection/frame_pipeline.py`, `app/annotation_obb/detection/frame_pipeline.py`, `app/annotation/sources/source_helpers.py`, `app/annotation_obb/sources/source_helpers.py`, `app/annotation/infrastructure/persistence/coco_storage.py`, `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`
- Impact: Fixes in standard detection do not automatically apply to OBB, and shared behaviors such as autosave, restoration, deletion, source traversal, and status updates can drift.
- Fix approach: Extract shared source traversal, persistence lifecycle, autosave, and frame navigation helpers into neutral modules under `app/annotation/core/` or `app/annotation/infrastructure/`, then keep OBB-specific geometry isolated under `app/annotation_obb/geometry/`.

**Legacy monolithic annotation script remains in the repository:**
- Issue: `utils/annotation_tool_bytetracked.py` contains a 1000+ line standalone annotation implementation with its own constants, parsing, persistence, and UI.
- Files: `utils/annotation_tool_bytetracked.py`, `app/annotation/tool.py`, `app/annotation_tool.py`
- Impact: Future fixes can land in the wrong implementation, and behavior copied from the utility may bypass the modular app and tests.
- Fix approach: Mark `utils/annotation_tool_bytetracked.py` as legacy in documentation or replace it with a thin migration/compatibility script that imports the modular app services.

**Dependency versions are not reproducible for Python and Rust:**
- Issue: `requirements.txt` has unpinned Python packages, `frontend/src-tauri/Cargo.toml` uses broad Rust dependency versions, and no `frontend/src-tauri/Cargo.lock` is present.
- Files: `requirements.txt`, `build.sh`, `frontend/src-tauri/Cargo.toml`, `frontend/package-lock.json`
- Impact: Fresh installs can silently pick different `ultralytics`, `opencv-python`, `fastapi`, `uvicorn`, `tauri`, or `tauri-plugin-shell` versions. Build and runtime behavior may change without code changes.
- Fix approach: Pin Python dependencies or generate a lockfile, commit `frontend/src-tauri/Cargo.lock` for the app, and keep `frontend/package-lock.json` as the Node source of truth.

**Broad exception handling hides actionable failures:**
- Issue: Many paths catch `Exception` and return `None`, `[]`, or log to stdout without structured error propagation.
- Files: `app/annotation/application/lifecycle.py`, `app/annotation/detection/frame_pipeline.py`, `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`, `app/core/startup_cache.py`, `app/runner.py`
- Impact: Corrupt state, failed autosave, failed inference, and persistence errors can look like normal empty states. Debugging relies on console output in a GUI app.
- Fix approach: Reserve broad catches for UI boundaries, return typed result objects from persistence/model operations, and surface user-visible errors through status variables or API responses.

## Known Bugs

**React/Tauri production API path is not wired like development:**
- Symptoms: Frontend requests use `BASE = "/api"`, but only Vite dev server config proxies `/api` to `http://127.0.0.1:8765`. A built Tauri webview does not show an equivalent `/api` proxy in config or Rust code.
- Files: `frontend/src/api/client.ts`, `frontend/vite.config.ts`, `frontend/src-tauri/tauri.conf.json`, `frontend/src-tauri/src/lib.rs`, `api_server.py`
- Trigger: Build the Tauri app and open the React UI outside the Vite dev server.
- Workaround: Run the frontend through Vite dev mode, or change the production client to call the loopback backend URL explicitly and gate it by environment.

**React annotations disappear after frame navigation:**
- Symptoms: `addAnnotation` updates the current Zustand frame, but `/frames/current`, `/frames/next`, and `/frames/prev` always return `annotations=[]`. Existing annotations are not fetched from `/annotations/{image_id}` when frames load.
- Files: `frontend/src/stores/annotation.ts`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `frontend/src/components/canvas/AnnotationCanvas.tsx`
- Trigger: Add an annotation, navigate to another frame, then navigate back.
- Workaround: None in the React UI. Use the Tkinter implementation for persisted annotation work.

**React session totals are stale after frame initialization:**
- Symptoms: `start()` calls `/frames/init` but ignores the returned `total`; it stores `totalFrames` from `/session/start`, which is always `0`.
- Files: `frontend/src/stores/session.ts`, `app/api/routes/session.py`, `app/api/routes/frames.py`
- Trigger: Start a React session with a valid image directory.
- Workaround: Consumers using `FrameResponse.total` remain correct after `fetchFrame()`, but session-level totals stay wrong.

**Save, export, settings, and tool buttons in React have no behavior:**
- Symptoms: Topbar buttons render save/export/settings icons without `onClick` handlers; sidebar tool controls are display-only `div` elements.
- Files: `frontend/src/components/layout/Topbar.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/stores/annotation.ts`, `app/api/routes/annotations.py`
- Trigger: Click save, export, settings, or sidebar tool controls in the React annotation screen.
- Workaround: Use the Tkinter UI for save/export workflows.

**React canvas can submit out-of-image boxes:**
- Symptoms: Mouse positions are converted to image coordinates without clamping to image bounds. API schemas accept any float list for `bbox`.
- Files: `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/stores/annotation.ts`, `app/api/schemas.py`, `app/api/routes/annotations.py`
- Trigger: Drag a rectangle starting or ending outside the displayed image area.
- Workaround: Avoid drawing outside the image in the React UI.

## Security Considerations

**Tauri security surface is broad for the current feature set:**
- Risk: CSP is disabled and shell plugin capabilities include `open` and `sidecar`.
- Files: `frontend/src-tauri/tauri.conf.json`, `frontend/src-tauri/src/lib.rs`
- Current mitigation: Backend binds to `127.0.0.1` in `api_server.py`, and the configured frontend origins are local in `app/api/main.py`.
- Recommendations: Add a production CSP, narrow shell plugin permissions, define the expected sidecar explicitly, and avoid enabling shell open globally unless a feature requires it.

**Local API has no authentication or per-session authorization:**
- Risk: Any allowed local origin can call the annotation API and pass arbitrary local filesystem paths as `data_root` and `output_dir`.
- Files: `app/api/main.py`, `app/api/routes/session.py`, `app/api/schemas.py`, `frontend/vite.config.ts`
- Current mitigation: Uvicorn listens on `127.0.0.1`, and CORS allowlist is limited to local development/Tauri origins.
- Recommendations: Keep loopback binding mandatory, validate and normalize user-selected paths, add a simple local session token for browser-origin calls, and avoid broad CORS expansion.

**Export code can delete existing directories selected as dataset roots:**
- Risk: YOLO export removes `dataset_root` before writing output.
- Files: `app/annotation/infrastructure/export/yolo_exporter.py`, `utils/merge_yolo_splits.py`, `tests/test_dataset_export.py`
- Current mitigation: Tests cover some export-root selection behavior in `tests/test_dataset_export.py`.
- Recommendations: Keep all destructive export paths below explicit generated-output roots, require confirmation before deleting non-generated directories, and use a marker file to identify managed export directories.

**User filesystem paths are persisted in local cache and COCO metadata:**
- Risk: Absolute dataset, model, output, and source paths are written to `.local/startup_cache.json` and annotation metadata.
- Files: `app/core/startup_cache.py`, `app/annotation/infrastructure/persistence/coco_storage.py`, `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`, `.gitignore`
- Current mitigation: `.local/` is ignored by `.gitignore`; generated datasets and outputs are ignored.
- Recommendations: Keep `.local/` ignored, avoid adding cache files to artifacts, and consider relative path storage for shareable annotation states.

**Build script downloads and installs mutable dependencies:**
- Risk: `build.sh` downloads Miniconda and installs unpinned requirements and PyInstaller ranges during the build.
- Files: `build.sh`, `requirements.txt`
- Current mitigation: Downloads use HTTPS and build output is local.
- Recommendations: Pin package versions, verify installer checksums, and separate environment bootstrap from release packaging.

## Performance Bottlenecks

**Frame API encodes full images as base64 on every request:**
- Problem: `/frames/current`, `/frames/next`, `/frames/prev`, and `/frames/goto/{index}` read images with OpenCV, JPEG-encode them, and return base64 strings inline.
- Files: `app/api/routes/frames.py`, `frontend/src/stores/annotation.ts`, `frontend/src/components/canvas/AnnotationCanvas.tsx`
- Cause: The API has no thumbnail/cache/static image serving path.
- Improvement path: Serve images through a local file endpoint or object URL, cache encoded frames by path and mtime, and provide scaled previews for canvas display.

**Frame discovery recursively scans the full data root:**
- Problem: `/frames/init` uses `root.rglob("*")` for all supported image extensions.
- Files: `app/api/routes/frames.py`, `app/core/session.py`
- Cause: No indexed source discovery or pagination is used by the API path.
- Improvement path: Reuse source discovery services from `app/annotation/sources/source_discovery.py` and cache frame paths per session.

**Autosave rewrites full COCO JSON and image files frequently:**
- Problem: The Tkinter lifecycle autosaves before switching frames and on shutdown; persistence writes the entire annotations payload.
- Files: `app/annotation/application/lifecycle.py`, `app/annotation/infrastructure/persistence/coco_storage.py`, `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`
- Cause: State is kept as full in-memory `images` and `annotations` lists and serialized wholesale.
- Improvement path: Keep current behavior for small datasets, but add dirty-frame tracking, atomic writes, and batched persistence before scaling to very large projects.

**OBB inference runs synchronously in the frame pipeline:**
- Problem: Standard detection runs model inference on a background thread, while OBB calls `self.run_model(frame)` directly during `process_current_frame`.
- Files: `app/annotation/detection/frame_pipeline.py`, `app/annotation_obb/detection/frame_pipeline.py`
- Cause: The OBB pipeline has its own implementation rather than sharing the threaded detection pattern.
- Improvement path: Port the frame-index snapshot/background-apply pattern from `app/annotation/detection/frame_pipeline.py` into OBB or extract a shared async inference helper.

**OBB image lookup remains linear:**
- Problem: Standard COCO storage builds `_image_index`; OBB storage scans `self.images` for each lookup.
- Files: `app/annotation/infrastructure/persistence/coco_storage.py`, `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`, `tests/test_annotation_storage_perf.py`
- Cause: OBB persistence did not inherit the cache optimization covered for standard annotations.
- Improvement path: Add the same invalidated index cache to `OBBCocoStorageMixin` and cover it with an OBB-specific performance test.

## Fragile Areas

**Annotation tool contracts are implicit across mixins:**
- Files: `app/annotation/tool.py`, `app/annotation_obb/tool.py`, `app/annotation/ui/mouse_events.py`, `app/annotation/detection/selection_edit.py`, `app/annotation/core/services/class_service.py`
- Why fragile: Mixins depend on attributes such as `current_frame`, `canvas`, `images`, `annotations`, `target_classes`, and `undo_stack` that are initialized in other mixins.
- Safe modification: Before changing a shared attribute or method name, search both `app/annotation/` and `app/annotation_obb/`, then add a composed-tool contract test under `tests/`.
- Test coverage: `tests/test_obb_tool_contract.py` checks some OBB method presence, but there is no broad composed-tool smoke test for every annotation mode.

**Class/category remapping affects multiple caches and export formats:**
- Files: `app/annotation/core/services/class_service.py`, `app/annotation/core/export/yolo_label_service.py`, `app/annotation/infrastructure/export/yolo_exporter.py`, `tests/test_class_removal.py`, `tests/test_class_order.py`
- Why fragile: Removing or reordering classes must update categories, annotations, model/manual detection caches, YOLO label mappings, and UI state.
- Safe modification: Use `ClassServiceMixin` as the entry point for class mutations and extend existing class-removal/order tests when changing category ID semantics.
- Test coverage: Unit coverage exists for class removal and export order, but frontend class selection in `frontend/src/components/layout/Sidebar.tsx` is not covered.

**Startup wizard is a large UI module:**
- Files: `app/ui/startup/wizard.py`, `app/ui/startup/intro.py`, `app/core/session.py`, `app/core/startup_cache.py`
- Why fragile: `app/ui/startup/wizard.py` is over 1300 lines and combines layout, validation, saved-state handling, cache persistence, and session creation.
- Safe modification: Keep validation and state discovery changes in `app/core/session.py` and `app/core/output_state.py` where possible; avoid adding new filesystem logic directly to the wizard.
- Test coverage: Core session/cache/output-state behavior is tested in `tests/test_session_config.py`, `tests/test_session_installer.py`, and `tests/test_output_state.py`; wizard UI interactions are not automated.

**Build and packaging are centralized in one shell script:**
- Files: `build.sh`, `requirements.txt`, `main.py`, `app/runner.py`, `frontend/src-tauri/tauri.conf.json`
- Why fragile: `build.sh` handles environment creation, dependency installs, PyInstaller hidden imports, smoke tests, and OS shortcut registration in one script.
- Safe modification: Keep release changes small, test on the target OS, and split reusable packaging checks into separate scripts before adding Tauri packaging.
- Test coverage: CI does not run `build.sh` or Tauri packaging.

**Tauri sidecar lifecycle is unmanaged:**
- Files: `frontend/src-tauri/src/lib.rs`, `api_server.py`, `app/api/main.py`
- Why fragile: The sidecar child handle is local to setup, with no explicit readiness check, restart logic, shutdown path, or frontend health gate.
- Safe modification: Store/manage the child process in Tauri state, poll `/health` before enabling UI actions, and terminate the backend on application exit.
- Test coverage: No Rust/Tauri tests or packaging smoke tests are present.

## Scaling Limits

**Single global API session:**
- Current capacity: One active API session per backend process.
- Limit: Multiple windows, users, or background tasks overwrite the same `runtime`, `_frame_paths`, `_current_index`, and `_store`.
- Scaling path: Introduce session IDs and per-session state objects in `app/api/state.py`, then make route handlers operate on explicit session state.

**In-memory annotation API storage:**
- Current capacity: Manual annotations created in the React UI remain only in process memory.
- Limit: Backend restart, Tauri sidecar crash, or route reload loses unsaved work.
- Scaling path: Persist through `app/annotation/infrastructure/persistence/coco_storage.py` and load annotations per frame through a storage-backed query.

**COCO JSON payload grows as one file:**
- Current capacity: Full payload rewrites work for small and medium annotation projects.
- Limit: Large datasets increase save latency and risk losing recent edits if a write is interrupted.
- Scaling path: Use atomic temp-file replacement, consider append-only change logs or per-frame state shards, and keep a compact final export step.

**Frontend frame transport scales poorly with image size:**
- Current capacity: One JPEG base64 payload per current frame.
- Limit: Large images or rapid navigation increase CPU, memory, and JSON payload size.
- Scaling path: Serve binary image responses, use browser object URLs, and pass annotation metadata separately from image bytes.

## Dependencies at Risk

**Ultralytics/OpenCV/PyTorch transitive stack:**
- Risk: `ultralytics` pulls a large model/runtime stack and is not pinned in `requirements.txt`.
- Impact: Model loading, PyInstaller hidden imports, and inference behavior can change across installs.
- Migration plan: Pin known-good versions, record GPU/CPU support expectations, and keep build hidden imports synchronized with those versions in `build.sh`.

**Native tracking packages (`lap`, `cython-bbox`):**
- Risk: Native builds are platform-sensitive and documented as requiring compiler tooling.
- Impact: Fresh installs can fail on Windows/Linux machines without build tools, or fall back to slower alternatives if optional packages are missing.
- Migration plan: Keep the SciPy fallback in `tracker/matching.py`, publish tested wheels/version pins, and make CI cover fallback behavior without requiring native packages.

**Tauri dependency resolution:**
- Risk: Rust dependencies use broad major versions and no app lockfile is committed.
- Impact: Tauri plugin behavior and security defaults can change across machines.
- Migration plan: Commit `frontend/src-tauri/Cargo.lock` and update Tauri dependencies intentionally.

**Frontend dependency freshness:**
- Risk: `frontend/package.json` uses caret ranges for React, Vite, Tauri API packages, Radix packages, and Zustand.
- Impact: Local installs without the lockfile, or lockfile refreshes, can introduce UI/runtime changes.
- Migration plan: Keep `frontend/package-lock.json` committed and run `npm ci` in CI; update dependencies through explicit maintenance PRs.

## Missing Critical Features

**React/Tauri save and export workflow:**
- Problem: The React UI has visual controls for save/export, but no API routes or frontend handlers implement persisted save/export.
- Files: `frontend/src/components/layout/Topbar.tsx`, `frontend/src/stores/annotation.ts`, `app/api/routes/annotations.py`, `app/api/main.py`, `app/annotation/infrastructure/persistence/export_actions.py`
- Blocks: React/Tauri cannot replace the Tkinter UI for real annotation production work.

**React/Tauri mode parity:**
- Problem: The wizard allows `tracking`, `detection`, `obb`, and `classification`, but the API/frame/canvas implementation only supports simple rectangle annotations over images.
- Files: `frontend/src/components/wizard/Wizard.tsx`, `frontend/src/components/canvas/AnnotationCanvas.tsx`, `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`
- Blocks: Tracking IDs, OBB geometry editing, classification workflows, model inference review, ROI, homography, and export parity are unavailable in React/Tauri.

**API-backed resume existing annotations:**
- Problem: `resume_existing` is accepted in the API request but the route does not load existing annotations or output state.
- Files: `app/api/schemas.py`, `app/api/routes/session.py`, `app/core/output_state.py`, `app/annotation/infrastructure/persistence/coco_storage.py`
- Blocks: React/Tauri sessions cannot resume the persisted annotation states supported by the Tkinter path.

**Frontend path selection integration:**
- Problem: React wizard fields collect paths as plain strings; there is no Tauri file/folder picker integration visible in the checked-in frontend code.
- Files: `frontend/src/components/wizard/Wizard.tsx`, `frontend/src/components/wizard/StepData.tsx`, `frontend/src/components/wizard/StepConfig.tsx`, `frontend/src-tauri/Cargo.toml`
- Blocks: Desktop users must type paths manually, increasing invalid path errors and reducing parity with the Tkinter startup wizard.

## Test Coverage Gaps

**CI does not fail on backend test failures:**
- What's not tested: Required Python unit-test health as a blocking gate.
- Files: `.github/workflows/ci.yml`, `tests/`
- Risk: Broken persistence/export/session logic can merge.
- Priority: High

**FastAPI routes are untested:**
- What's not tested: Session start/stop, frame init/navigation, annotation CRUD, class listing, validation errors, and cross-route state behavior.
- Files: `app/api/main.py`, `app/api/routes/session.py`, `app/api/routes/frames.py`, `app/api/routes/annotations.py`, `app/api/routes/classes.py`
- Risk: React/Tauri regressions ship without detection.
- Priority: High

**React UI and stores are untested:**
- What's not tested: Wizard submission, annotation store navigation, canvas coordinate conversion, class selection, topbar actions, and error states.
- Files: `frontend/src/stores/session.ts`, `frontend/src/stores/annotation.ts`, `frontend/src/components/canvas/AnnotationCanvas.tsx`, `frontend/src/components/wizard/Wizard.tsx`
- Risk: UI-visible bugs are only found manually.
- Priority: High

**Tauri sidecar and production packaging are untested:**
- What's not tested: Sidecar discovery, backend startup readiness, production API URL behavior, child-process shutdown, and bundled app smoke tests.
- Files: `frontend/src-tauri/src/lib.rs`, `frontend/src-tauri/tauri.conf.json`, `api_server.py`, `frontend/src/api/client.ts`
- Risk: The app can work in dev and fail after packaging.
- Priority: High

**Tkinter UI behavior has limited automation:**
- What's not tested: Startup wizard interactions, annotation canvas mouse workflows, keyboard shortcut behavior in live windows, autosave UI feedback, and export dialogs.
- Files: `app/ui/startup/wizard.py`, `app/annotation/ui/mouse_events.py`, `app/annotation/keybinds/keybind_mixin.py`, `app/annotation/presentation/export/export_screen.py`
- Risk: Refactors can break production UI workflows while pure domain tests pass.
- Priority: Medium

**OBB persistence and performance lag standard detection coverage:**
- What's not tested: Indexed image lookup, large annotation restore performance, and full OBB resume/delete/export parity.
- Files: `app/annotation_obb/infrastructure/persistence/obb_coco_storage.py`, `app/annotation_obb/infrastructure/export/yolo_obb_exporter.py`, `tests/test_yolo_obb_export.py`, `tests/test_obb_geometry.py`
- Risk: OBB behavior drifts from the better-tested standard detection path.
- Priority: Medium

---

*Concerns audit: 2026-06-02*
