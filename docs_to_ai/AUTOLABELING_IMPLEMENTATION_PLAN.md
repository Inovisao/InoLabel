# Autolabeling implementation plan

Status: partially implemented. The local detection workflow is implemented; the
full roadmap below remains the target, not a claim that every phase is complete.

## Current delivery

- Local YOLO checkpoint inspection and explicit class mapping.
- Immutable image/checkpoint snapshots and project-local run/proposal manifests.
- Current-image, selected-image, and dataset jobs with progress, cancellation,
  interruption detection, paginated results, and resume of incomplete work.
- Review, geometry/class edits before acceptance, rejection, durable acceptance,
  recovery after interrupted receipt updates, and acceptance-aware undo.
- Editor toolbar/panel, separate canvas proposal layer, and a dedicated project view
  that does not stop the annotation session.
- Shared runtime mutation locking and fixes to legacy confidence/class mapping and
  persisted-label loading.

Additional delivery: task-filtered model catalog, typed model-specific input schemas,
shared schema-driven forms, independent model drafts, a SAM 3 adapter through an
isolated Roboflow Inference worker, and a curated Ollama vision catalog with background
downloads and prompt-driven box proposals. SAM 3 requirements are pinned separately;
explicit preparation downloads/caches weights using a backend API key.
See [foundation integrations](FOUNDATION_MODEL_INTEGRATIONS.md) for setup and scope.

Not implemented: tracking proposals in the new flow, Grounding DINO, full
segmentation annotation/export, and OpenAI.
No real-model quality or hardware evaluation has been completed. The concrete
initial layout uses focused `models.py`, `service.py`, `jobs.py`, `storage.py`, and
`adapters/` modules; introduce further layers only when their responsibilities grow.
Related design: [Autolabeling architecture](AUTOLABELING_ARCHITECTURE.md).

## Product scope and initial decisions

Build a project-scoped autolabeling workspace and an integrated editor panel.
Both use the same configuration, jobs, proposals, and review services. Keep the
existing annotation canvas and accepted-annotation store authoritative.

Initial delivery: local YOLO bounding-box suggestions on the current image in
detection mode, with explicit class mapping, preview, acceptance, and rejection.
Then add selected-image/dataset batches, tracking, and foundation-model adapters.
Keep manual annotation usable when no model runtime is installed.

Use two visible workflows: Trained model and Foundation models. Internally use
`trained_model` and `prompt_based`. Capabilities determine available tasks and
controls; a provider name does not determine the task.

Segmentation is a separate milestone: a SAM mask preview is not full segmentation
annotation support. No external provider is contacted during this planning work.

## Phase 0 — Contracts and baseline regression coverage

Deliverables:

- Introduce task, model, prompt, run, and proposal contracts under
  `app/autolabeling/domain/`; add application ports as they become necessary.
- Define original-image pixel coordinates, box endpoint semantics, stable media
  identity, explicit class bindings, and typed/optional scores.
- Define project and taxonomy revisions before jobs or review depend on them.
  Distinguish taxonomy/input changes from ordinary annotation additions.
- Record a migration matrix for existing detection/tracking sessions and saved state.
- Add regression cases for class-name mismatch, invalid checkpoint paths, confidence
  propagation, unread persisted labels, and project switching during work.

Acceptance:

- A model class cannot silently become a project class based on numeric position.
- Contracts distinguish pending suggestions from accepted annotations.
- Existing saved projects open and manual annotation behavior remains unchanged.

## Phase 1 — Safe local YOLO integration

Deliverables:

- Wrap `app/core/detector.py` behind a lazy Ultralytics adapter; avoid duplicate
  model-loading logic and unnecessary changes to the tracker.
- Register model configuration independently of session creation. Validate regular
  file, supported task, vocabulary, and readable checkpoint during an explicit test.
- Support detection without a tracker. Reject incompatible tasks clearly.
- Persist model/class mappings and effective thresholds in the run snapshot.
- Generate proposals for one immutable image input without modifying annotation state.
- Introduce proposal/run storage under the project using atomic writes and stable IDs.
- Keep the legacy inference endpoint available while the new path is introduced;
  fix its data-preservation issues before treating it as a compatibility wrapper.

Acceptance:

- A local checkpoint produces mapped box proposals on a sample image.
- Bad weights, missing dependencies, and incompatible tasks produce actionable errors.
- Model failure or zero detections does not erase labels or mark a frame reviewed.
- No model loads merely because the app or registry page opens.

## Phase 2 — Review, acceptance, and durable persistence

Deliverables:

- Implement an annotation gateway using existing validation, label paths, ID
  allocation, and state persistence. Load saved state before applying proposals.
- Add accept/reject operations with proposal IDs and expected input/taxonomy revisions.
- Serialize acceptance against all manual mutations of the same project; an isolated
  lock used only by autolabeling would not protect shared state.
- Define a recoverable commit record: pending commit identity, persisted annotation
  IDs/provenance, and a completion receipt. Recovery reconciles interruptions between
  annotation persistence and proposal status updates without creating duplicates.
- Extend persistence with per-commit completion/error acknowledgement. A writer flush
  that only drains the queue is insufficient evidence of successful disk writes.
- Define batch results with accepted, persisted, failed, and stale counts.
- Support edits before acceptance and separate generated origin from human review.
- Define undo for acceptance: remove only the created annotations and reconcile the
  proposal receipt/status. Do not reuse generic deletion without updating provenance.

Acceptance:

- Retrying acceptance creates no duplicate annotations, including after restart.
- Existing manual annotations and human corrections survive re-runs.
- A disk error is visible and cannot be reported as a successful durable save.
- Stale class mappings or changed input images cannot be silently accepted.
- Undo and re-accept have defined, tested behavior.

## Phase 3 — First complete editor workflow

Integration points:

- `frontend/src/features/annotate/Topbar.tsx`: Autolabeling action/status.
- `AnnotatePage.tsx`: panel and review-mode composition.
- `canvas/AnnotationCanvas.tsx`: separate proposal layer using existing transforms.
- `store/undoSlice.ts` and related types: acceptance-aware undo integration.
- `frontend/src/features/autolabeling/`: model controls, review, API hooks, and state.
- `frontend/src/shared/api/client.ts`: reuse transport and error handling.

Deliverables:

- Add an editor panel for model selection, explicit class mapping, confidence,
  current-image generation, sample errors, and execution status.
- Draw proposals in a separate layer with a distinct style and a visibility toggle.
  Proposals do not enter normal annotation state or exports before acceptance.
- Add Accept, Edit and accept, Reject, and Accept selected actions.
- Preserve model configuration across frame navigation; scope state by project/run.
- Define keyboard focus so typing prompts does not trigger annotation shortcuts.
- Support loading, unavailable model, failed inference, no results, and stale-result states.
- Refresh accepted frame state from the server and retain appropriate selection/undo.

Acceptance:

- A user imports YOLO, tests the current image, edits a suggestion, accepts it,
  reloads the project, and exports the result without leaving the editor.
- Rejected/pending proposals do not appear in exports.
- Canvas zoom, rotation, resize, and coordinate conversion remain correct.

Milestone A: useful end-to-end local autolabeling for the current image.

## Phase 4 — Background batches and tracking

Deliverables:

- Add bounded project-scoped job execution, per-frame outcomes, paginated proposals,
  progress, cancellation, and resumable manifests. Start with polling for status.
- Support current image, explicitly selected images, and the whole dataset.
- Pass immutable project/media/configuration snapshots to workers. Workers do not
  read or mutate `_state.active_session()` or shared frame arrays.
- On application restart, mark interrupted jobs and offer explicit resume using
  verified input/model/configuration fingerprints.
- Continue completed proposals after a partial failure; record unreadable images
  as failures rather than empty successful predictions.
- Add optional tracking as a pipeline step with ordered frames, run-local tracker
  state, and acceptance-time mapping into noncolliding project track IDs.
- For video, initially preserve preview-only behavior unless stable extracted-frame
  identities, timestamps, persistence, and review navigation are implemented together.
  Do not advertise video autosave as part of the image-batch milestone.

Acceptance:

- UI remains usable during a batch; switching frames does not change worker inputs.
- Cancellation preserves completed proposals; resume does not repeat completed work.
- Two runs cannot contaminate each other's state or overwrite manual labels.
- Tracking tests cover ordering, gaps, repeated runs, and existing project IDs.

## Phase 5 — Dedicated workspace and editor navigation

Deliverables:

- Add a project-scoped Autolabeling page with workflow choice, configuration,
  sample testing, run history, progress, and a Review results action.
- Add a Models and connections view, initially containing only implemented adapters.
- Refactor `App.tsx` view selection and `AnnotatePage.handleNavRequest`: navigating
  between editor and autolabeling must not call session stop or reset annotations.
- Keep project closing distinct from view navigation. Pending jobs remain bound to
  the originating project; closing a view is not cancellation.
- Review results opens the existing editor with run/frame filters and proposal selection.
- Migrate the wizard's checkpoint field into model configuration with a compatibility
  path for old requests; remove misleading automatic-labeling promises.

Acceptance:

- Both entry points show the same configurations and run results.
- Leaving and returning to the editor preserves current frame and project state.
- Another project cannot receive acceptance intended for an inactive project.
  Initially require activating that project before committing proposals.

Milestone B: complete local YOLO workflow for image batches and review.

## Phase 6 — Prompt-based detection and runtime isolation

Deliverables:

- Define a versioned local-worker protocol for capabilities, inference, health,
  artifacts, and errors; test it against an isolated runtime before adding SAM.
- Add Grounding DINO as the first prompt-based detection experiment.
- Add per-class descriptions, allowed class bindings, adapter-specific thresholds,
  and sample preview controls to the existing panel/workspace.
- Keep foundation dependencies outside the base app environment; preserve Python
  compatibility of the main application and manual annotation packaging.
- Evaluate a manually reviewed representative sample for precision, recall,
  localization, review time, latency, and memory. Record model/configuration revisions.

Acceptance:

- A text description produces box proposals reviewed through the same UI as YOLO.
- Unsupported runtimes/models disable only their own workflow.
- Results and failure modes are measured before enabling dataset-wide use by default.

## Phase 7 — SAM and segmentation

Decision gate: choose a SAM version and supported hardware, and decide whether
masks are intermediate artifacts or fully editable/exportable project annotations.

Deliverables:

- Add spatial prompt contracts, positive/negative point controls, and a SAM adapter.
- Support detector-box-to-mask composition and/or direct text segmentation when
  the selected SAM version supports it.
- Store mask artifacts with dimensions/transforms and model/prompt provenance.
- For full segmentation, add a task mode, geometry schema, persistence migration,
  mask editing/review, and appropriate COCO/YOLO segmentation export support.
- Make mask-to-box conversion explicit for detection projects.

Acceptance:

- Prompts and masks align with original pixels at all supported viewport transforms.
- Holes and disconnected components are not silently lost.
- Saved segmentation projects reopen correctly and export valid annotations.
- Mask preview alone is not presented as completed segmentation support.

## Phase 8 — Ollama and optional OpenAI integration

Deliverables:

- Start with one vision model through Ollama for classification or region verification.
- Validate image-input capability, allowed classes, structured output, timeouts,
  malformed responses, and absent/uncalibrated scores.
- Add an OpenAI adapter only after choosing remote execution as a supported option.
- Add backend-managed credentials, explicit external-data destination choice,
  request limits, cost visibility when available, and bounded retry policies.
- Update privacy documentation before any feature sends images off the machine.
- Reuse proposal review and classification services; do not force classification
  into a bounding-box schema or silently turn model descriptions into new classes.

Acceptance:

- The same classification use case can select compatible local/remote providers.
- No credential appears in the frontend bundle, project manifest, or logs.
- A remote outage never triggers an undisclosed provider switch or loss of annotations.

## Proposed API delivery order

1. Models: list/register configurations and explicitly test one sample.
2. Runs: submit and retrieve current-image runs/proposals.
3. Review: accept/reject proposals with revisions and recoverable receipts.
4. Batches: progress, cancellation, pagination, interruption recovery/resume.
5. Optional worker/provider management as actual adapters require it.

Use `/api/autolabeling/` for new routes. Keep HTTP schemas in the API layer and
business rules in application/domain modules. Do not create unused API routes or
adapter stubs for future phases.

## Validation and release discipline

- Each phase delivers behavior, regression coverage, documentation, and an explicit
  acceptance demonstration. Keep changes reviewable; split large phases across PRs.
- Backend: affected tests per PR, then full suite for shared contracts/persistence.
- Frontend: type checks, unit tests, build, and a manual editor acceptance walkthrough.
- Use fake adapters for deterministic failure/concurrency tests; use a trusted real
  checkpoint and representative sample for integration/quality evaluation.
- Test project switching, unread labels, duplicate class names, class edits, repeated
  acceptance, crash recovery, disk failure, and cancellation at the relevant phase.
- Maintain backward compatibility and keep the legacy path until replacements pass
  their acceptance criteria; document any intentional behavior changes.
- Avoid a distributed queue, generic plugin loader, pipeline graph editor, or
  automatic multi-model agents in the initial implementation.

## Recommended execution order

Phases 0–3 form Milestone A. Phases 4–5 form Milestone B. Only then select the
foundation-model branch based on evaluated data and available hardware. Phase 8
classification can follow Phase 6 independently of full segmentation.

No calendar estimate is assigned before checking model availability, target hardware,
and the first persistence/UI implementation. Completion is defined by phase exit
criteria, not by the presence of directories or placeholder classes.
