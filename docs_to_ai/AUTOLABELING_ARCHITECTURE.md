# Autolabeling architecture proposal

Status: target architecture with a partial local YOLO implementation. Research date: 2026-10-27.
See [implementation status](AUTOLABELING_IMPLEMENTATION_PLAN.md#current-delivery) for delivered features.

## Intent and terminology

Create one autolabeling module with two user-facing workflows:

- **Trained-model labeling:** apply a task-specific checkpoint, initially YOLO.
- **Prompt-based labeling:** apply pretrained foundation models without task-specific
  training, initially open-vocabulary detection, then segmentation and classification.

The interface may call these **Pseudolabeling** and **Zero-shot labeling**, but these
are not mutually exclusive scientific categories. Zero-shot predictions can also
become pseudo-labels. Zero-shot describes adaptation to the target task/classes;
pseudo-label describes the origin of labels. A generic YOLO checkpoint is not
necessarily trained for the user's classes, and a foundation model can be fine-tuned.
Record the actual model, revision, adaptation, and prompting configuration.

Use `trained_model` and `prompt_based` as workflow identifiers. Reserve adaptation
metadata such as `zero_shot`, `few_shot`, `fine_tuned`, or `unknown` for evaluation
and provenance. Do not infer adaptation from a provider name or file extension.
Spatial prompting without examples is distinct from few-shot example conditioning.

## Baseline reviewed before implementation

- The wizard submits a local checkpoint path and a confidence setting.
- Session startup checks path existence and the `.pt` suffix; this does not validate
  the checkpoint contents, task, vocabulary, or even that the path is a regular file.
- `app/core/detector.py` lazily loads Ultralytics YOLO.
- `app/api/inference/` exposes tracking inference, with optional image annotation
  saving. Detection, classification, OBB, and pose are not supported by that endpoint.
- The frontend does not invoke the inference endpoint.
- Video inference rejects automatic saving; it is not a complete annotation workflow.
- Inference is tied to shared active-session frame and annotation state.
- There is no segmentation mode or mask geometry in the existing `Annotation` schema.

Fix or account for these existing issues during migration:

1. `detections._category_id` falls back to the numeric model class ID when names do
   not match. This can silently assign a prediction to an unrelated project class.
2. `save_model_annotations` preserves manual annotations already in memory but does
   not load persisted annotations before replacing a frame's model predictions.
3. The wizard confidence setting is not retained in `SessionState`; inference uses
   its own request threshold or defaults to 0.4.
4. Inference workers use global frame state and autosave against the active session.
   A project switch during inference can target the wrong project's state.
5. `saved_annotations` reports the requested flag; autosave can log and swallow
   failures, so the flag does not establish durable persistence.

These are code-review findings; this proposal does not claim they were fixed or
that inference was validated using real checkpoints.

## Separate four concepts

| Concept | Example | Purpose |
| --- | --- | --- |
| Workflow | trained model, prompt based | How the user configures a labeling run |
| Task/capability | detect boxes, segment instances, classify crops, track | What an operation consumes and produces |
| Model | YOLO checkpoint, Grounding DINO, SAM 2, SAM 3, a vision-language model | The algorithm and its parameters |
| Runtime/provider | in-process Ultralytics, isolated local worker, Ollama, OpenAI | Where and how inference executes |

Ollama is a runtime/API, not a labeling model. A GPT vision model and a SAM
segmenter do not have interchangeable output contracts simply because both accept
prompts. Provider compatibility does not prove model capability.

Recommended capabilities are `detect_boxes`, `segment_instances`, `classify_image`,
`classify_regions`, `produce_keypoints`, `produce_obb`, and `track_instances`.
A configured model advertises only the supported subset, together with accepted
prompt types, supported media, score meanings, and deployment requirements.

## Model roles supported by the research

| Adapter/model | Inputs | Outputs and intended role |
| --- | --- | --- |
| Ultralytics YOLO | Images + trained weights | Task-specific predictions; first migration target |
| Grounding DINO | Images + text labels/descriptions | Open-vocabulary boxes; natural initial zero-shot experiment |
| SAM 2 | Images/video + spatial prompts | Masks; refinement of user boxes or detector proposals |
| SAM 3 | Images/video + text or visual prompts | Concept-conditioned segmentation and tracking; evaluate separately |
| OpenAI vision model | Images/crops + instructions | Structured class/attribute suggestions and review assistance |
| Vision model through Ollama | Images/crops + instructions | Local class/attribute suggestions, subject to the selected model's capabilities |

JSON schema adherence validates output shape, not semantic or geometric accuracy.
Do not enable precise box or mask production for a general vision-language model
without a task-specific adapter and measured localization quality. OpenAI documents
limitations in precise spatial localization. Text-only models cannot label images.

## Suggested module layout

Create files incrementally as each feature is implemented; this is the intended
boundary map, not a request to create empty scaffolding.

```text
app/autolabeling/
  domain/
    models.py                 # model specs, tasks, proposals, run identity
    prompts.py                # typed prompt variants and class bindings
    capabilities.py           # capability descriptions and compatibility checks
    errors.py
  application/
    ports.py                  # small task-specific interfaces
    service.py                # validate and submit labeling requests
    pipelines/
      trained_model.py
      prompt_based.py
    review.py                 # accept/reject and revision checks
  infrastructure/
    adapters/
      ultralytics.py
      grounding_dino.py
      sam2.py
      sam3.py
      ollama.py
      openai.py
    model_registry.py         # explicit adapter factories and model configuration
    jobs.py                   # bounded execution, progress, cancellation
    proposal_store.py         # durable results and artifacts
    annotation_gateway.py     # integrate existing annotation/persistence services
app/api/autolabeling/
  router.py
  schemas.py
frontend/src/features/autolabeling/
  ...                         # configuration, sample preview, job status, review
workers/autolabeling/
  ...                         # optional isolated runtime entry points
```

Dependency direction: API and runtime adapters depend on application/domain contracts;
domain code does not import FastAPI, model SDKs, GPU frameworks, or active-session state.
Existing annotation modules remain authoritative for accepted annotations.

Patterns: adapters for provider integration; small ports for task contracts;
composed pipeline steps for multi-model workflows; a registry for explicit discovery;
a job service for execution; and a separate proposal/review lifecycle for persistence.
Avoid a plugin marketplace, dynamic code loading, or a general graph editor initially.

## Contracts

### ModelSpec

Store an internal model ID, adapter ID, checkpoint reference or remote model ID,
revision/hash when available, runtime reference, capabilities, supported prompt
variants, resource requirements, and optional provider-specific configuration.
Credentials are external secret references and must not be serialized into projects.

Registration inspects metadata and validates configuration. An explicit sample test
loads the model and validates output compatibility. A `.pt` path alone is insufficient.
Never load every model merely to list the registry.

### PromptSpec

Use a discriminated union, validated against capabilities:

- Text: instruction, target class descriptions, and explicit class bindings.
- Points: original-image coordinates, positive/negative labels, target class.
- Boxes: original-image coordinates and target class.
- Mask: artifact reference, dimensions, target class.
- Exemplars: optional image/region references; record these as example conditioning.

A pipeline may combine compatible prompts. Keep native model thresholds in typed
adapter settings rather than forcing all providers into one confidence field.
Do not expose SDK-specific payloads as the shared application contract.

### LabelingRunSpec

Include project ID, immutable dataset/media snapshot, project/class revision,
selected frame IDs or ordered video range, task, workflow, pipeline revision,
model configuration snapshots, prompts, class mapping, execution limits, and
proposal policy. Run identity must not depend on the currently active UI session.

### PredictionProposal

Include proposal/run/frame IDs, original image dimensions and identity, stable
class binding, discriminated geometry, typed scores, model/stage provenance,
prompt/configuration fingerprint, and review status.

Geometry variants: box, mask, OBB, keypoints, or image class. Classification must
not require a dummy box. Choose original-image pixel coordinates as the internal
spatial convention; adapters reverse resizing, padding, orientation, and cropping.
Document box endpoints and convert to the existing annotation bbox format only at
the annotation gateway. Preserve transforms for audit and testing.

Keep dataset images immutable. Preprocessing is model-specific and happens only
for inference: use pixel/edge budgets that preserve aspect ratio, and record the
transform needed to map results back to the original image. Do not impose one
global resize on all modalities or project data. For high-resolution inputs where
downscaling could erase small targets, use overlapping tiles and merge proposals
in original-image coordinates.

Keep masks as binary/RLE artifacts, with optional derived polygons. Do not force
masks into a four-corner box or silently lose holes and disconnected components.
If the project only accepts boxes, require an explicit mask-to-box conversion.
Full segmentation needs a separate supported annotation mode, editing UI, state
format, and exporters before masks can be accepted as segmentation annotations.

Scores retain their meaning: detection confidence, predicted mask quality, text
similarity, or uncalibrated self-report. Missing confidence is valid. Scores from
different models must not share one universal threshold or be averaged blindly.

### Task ports

Use separate interfaces for detection, segmentation, classification, and tracking.
Each accepts typed input and returns task-specific predictions. Share lifecycle,
health checks, cancellation, and model identity only where needed. A small pipeline
step adapter can compose these ports without requiring every provider to implement
unsupported methods. Unsupported combinations fail before a job is submitted.

## Example pipelines

1. Trained-model boxes: image → YOLO → explicit class mapping → box proposals.
2. Tracked boxes: ordered frames → detector → tracker → proposals with run-scoped
   track identities. Map those identities into project IDs only during acceptance.
3. Prompted detection: image + text targets → Grounding DINO → box proposals.
4. Prompted segmentation: image + text → detector boxes → SAM 2 → mask proposals.
5. Direct concept segmentation: image + text → SAM 3 → mask proposals.
6. Assisted refinement: user box/points → SAM → mask preview → review.
7. Classification: image/crop + taxonomy → vision model via Ollama or OpenAI →
   schema validation → permitted class binding → classification proposal.
8. Semantic verification: detector proposals → crops → vision model review →
   additional evidence; preserve geometry and the original prediction provenance.

Start with explicit pipeline presets. Do not let a language model generate and
execute arbitrary pipelines or mutate the project taxonomy automatically.

## Jobs, storage, and acceptance

Suggested lifecycle:
`queued → running → succeeded | partially_failed | failed | cancelled`.
Review state is independent: `pending → accepted | rejected | stale`.

- Use bounded local execution first; no distributed queue is required initially.
  One exclusive GPU operation per configured device is a reasonable initial policy.
- Publish progress and paginated frame results; avoid retaining all video frames
  and results in one blocking HTTP response.
- Persist proposals and per-frame outcomes atomically; allow resume without
  repeating completed frames. Record provider, model, prompt, and input identity.
- Cancellation stops scheduling new work; do not promise immediate cancellation
  of a GPU kernel or remote request. Retries must be bounded and account for costs.
- Missing/unreadable frames are explicit failures, not negative annotations.
  Zero detections must not automatically mark a frame reviewed without objects.
- Default to preview. Acceptance goes through existing mode validation, label path,
  ID allocation, and state writing. Preserve manual labels and source datasets.
- If re-running a model, replace only explicitly selected proposals or accepted
  labels owned by that run; never delete all annotations with `source='model'`.
- Load persisted state before merging. Check project/image/taxonomy revisions at
  acceptance; reject stale results or require an explicit remapping.
- Serialize commits per project and make acceptance idempotent using proposal IDs.
  Record proposal-to-annotation receipts only after a durable write; distinguish
  generated, accepted, and successfully persisted counts.
- Keep machine-generated origin and human review status as separate metadata.
  Editing a machine proposal must not make later runs silently overwrite it.

Persist run manifests, proposals, and mask artifacts under the project, for example
`.inolabel/autolabeling/runs/<run-id>/`. Use atomic files for the first version;
consider SQLite when query volume and transaction requirements justify it.
Do not store bulk masks inside the project manifest or transmit them all as JSON.

## Suggested API and user flow

Proposed endpoints, not existing functionality:

- `GET /api/autolabeling/models`: availability, capabilities, and requirements.
- `POST /api/autolabeling/models`: register configuration, not arbitrary executable code.
- `POST /api/autolabeling/models/{id}/test`: explicit sample inference.
- `POST /api/autolabeling/runs`: validate and submit; return a run ID.
- `GET /api/autolabeling/runs/{id}`: progress and per-frame failure summary.
- `POST /api/autolabeling/runs/{id}/cancel`.
- `GET /api/autolabeling/runs/{id}/proposals`: paginated, filterable results.
- `POST /api/autolabeling/runs/{id}/accept`: selected proposal IDs and expected revisions.
- `POST /api/autolabeling/runs/{id}/reject`.

User flow: choose workflow → task → compatible model/runtime → classes and prompts →
test a few images → inspect sample output → run a batch → review and accept.
Do not promise automatic labeling merely because a model path was selected.

## Runtime isolation and remote execution

The app CI currently targets Python 3.9. Official SAM 2 installation requires
Python >=3.10; official SAM 3 installation requires Python >=3.12 and specifies
CUDA/GPU prerequisites. Do not put these packages into the base requirements
without an explicit supported-environment migration.

Recommendation: keep a model-runtime boundary now. Migrate YOLO behind an in-process
adapter first; add an isolated local worker for foundation models with incompatible
requirements. The app can communicate through a small versioned local protocol.
This is a process boundary for dependency/resource isolation, not a requirement to
deploy microservices. Optional runtime dependencies must not prevent manual labeling.

Reuse bounded model instances; serialize mutable predictor state or create isolated
sessions. SAM embedding caches must include image identity, model revision, and
preprocessing configuration. Temporal models need ordered media and run-local state.

Ollama can be a local provider. OpenAI is a remote provider: adding it changes the
README's current statement that images never leave the computer. Keep local
execution as the default, display the actual destination, and require an explicit
remote-data choice before sending images or crops. Keep API keys in backend secrets,
not frontend bundles or project manifests. Configure timeouts, request budgets,
image limits, and rate limiting. Do not silently fall back from local to remote.

## Incremental delivery

1. Establish core proposal/run contracts and a YOLO adapter. Correct class mapping,
   confidence propagation, persistence handling, and active-session coupling.
   Preserve the legacy tracking endpoint as a compatibility wrapper during migration.
2. Add sample preview, background runs, proposal review, idempotent acceptance,
   progress, cancellation, and resume. Detection should work without a tracker.
3. Evaluate Grounding DINO on representative project images. Add explicit class
   descriptions and mappings; benchmark useful labels per review minute.
4. Choose a SAM version based on needed prompts and available hardware. Add spatial
   refinement or a composed detector→SAM pipeline. Implement segmentation editing,
   persistence, and exports before advertising full segmentation annotation.
5. Add one local vision-language model through Ollama for classification/verification,
   then an OpenAI adapter if remote execution is wanted. Reuse task contracts and
   schema validation; keep provider-specific behavior within adapters.

Each adapter needs contract tests for supported inputs, coordinate conversions,
class mapping, malformed output, missing dependencies, and provider failures.
Integration tests must cover partial failures, cancellation, project switching,
stale taxonomy, repeated acceptance, and preservation of existing annotations.
Quality evaluation should use a manually reviewed representative sample: precision,
recall, class confusion, mask/box IoU where relevant, review time, latency, memory,
and remote cost. No claim of model quality follows merely from successful execution.

## Open decisions before implementation

- Is full segmentation editing/export required immediately, or are masks initially
  intermediate artifacts used to derive boxes?
- Which hardware and operating systems must foundation-model workers support?
- Is sending images to external providers allowed for the intended datasets?
- Which model family wins a small representative evaluation on this project's data?
- Should the main application's Python baseline migrate later, independently of
  the initial isolated-worker approach?

## Primary research sources

These sources establish model capabilities and interfaces. Module boundaries,
contracts, storage policies, and delivery order above are architectural recommendations.

- [SAM 2 repository and installation](https://github.com/facebookresearch/sam2)
- [SAM 2 image predictor: spatial prompts and mask outputs](https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py)
- [SAM 3 repository: concept prompts and runtime requirements](https://github.com/facebookresearch/sam3)
- [Grounding DINO and composition with SAM](https://huggingface.co/docs/transformers/model_doc/grounding-dino)
- [Ollama vision inputs](https://docs.ollama.com/capabilities/vision)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [OpenAI image inputs and vision limitations](https://developers.openai.com/api/docs/guides/images-vision)
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
