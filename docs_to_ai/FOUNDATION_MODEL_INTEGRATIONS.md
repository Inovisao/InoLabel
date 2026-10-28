# Foundation model integrations

## Delivered scope

Autolabeling now separates **Modelo importado** from **Fundacional / público**.
The latter is a curated, task-filtered catalog containing SAM 3 and local Ollama
vision models for text-conditioned box proposals in detection projects. The existing YOLO workflow,
proposal review, acceptance, undo, and saved runs remain supported.

SAM 3 uses **local Roboflow Inference**, following the
[Roboflow SAM 3 weights guide](https://roboflow.com/blog/download-sam-3-weights).
The adapter initializes `SegmentAnything3(model_id="sam3/sam3_final", api_key=...)`
and calls `segment_image` with typed `Sam3Prompt` text inputs and polygon output.
One prediction may contain multiple disconnected polygons; their combined bounds
produce one box. Prompt indices and echoed text must match the submitted concepts.
Masks are intermediate output, not an editable or exportable segmentation mode.
GPT and Grounding DINO are extension targets, not registered adapters.

## Configure SAM 3

Use a separate Python environment for Roboflow. Its NumPy and SDK dependencies
must not replace the main application's pinned YOLO dependencies. Python 3.12 is
recommended for this optional runtime; the main application still supports 3.9.

```bash
conda create -n inolabel-sam3 python=3.12 pip
conda run -n inolabel-sam3 python -m pip install -r requirements-sam3.txt
conda run -n inolabel-sam3 python -c "import sys; print(sys.executable)"
```

The last command prints the executable to use below. The optional file pins
`inference-gpu[sam3]==1.1.2`, with PyTorch and torchvision declared explicitly
because the published SAM 3 extra does not declare them. Do not install this file
into the main application environment. GPU drivers and runtime compatibility still
need to match your machine; the real model has not been evaluated on this project's
supported hardware or operating systems.

Before starting the application's backend, set:

```bash
export INOLABEL_SAM3_PYTHON="/absolute/path/to/envs/inolabel-sam3/bin/python"
export ROBOFLOW_API_KEY="<your-private-api-key>"
# Activate the main application environment, then:
python main.py
```

On PowerShell, use `$env:INOLABEL_SAM3_PYTHON = "C:\path\to\python.exe"` and
`$env:ROBOFLOW_API_KEY = "<your-private-api-key>"` before launching the backend.
Obtain an authorized key and model access through Roboflow. Never put credentials
in project parameters, tracked files, screenshots, or a model prompt.

1. In a detection project, open Autolabeling → Fundacional / público → SAM 3 →
   Configurar modelo.
2. Click **Preparar modelo**. This explicit action initializes the local SDK and
   downloads/caches the weights if necessary. It can take several minutes. The app
   does not install Python packages, register an account, or accept terms for you.
3. Select target project classes and enter short visual concepts, such as `wasp`
   or `red apple`. Text is preserved without silent translation.
4. Adjust the minimum score and cross-prompt mask NMS threshold, then test the
   current image before a batch.
5. Review, edit, accept, or reject boxes in the existing annotation editor.

The SDK runs locally in a subprocess, retained for the duration of a labeling job.
This integration does not call a hosted image inference endpoint. Roboflow may
require network access for authorization, artifact downloads, and SDK services;
this is not an offline-mode guarantee. Model logs and raw provider exception text
are not returned through the API because they can contain the private API key.
A configured catalog entry means runtime metadata and prepared cache were found;
it does not mean inference quality or hardware compatibility has been verified.

Weights and preparation metadata live under
`<INOLABEL_LOCAL_DIR>/autolabeling/runtimes/sam3/`; by default this is inside the
ignored `.local/` directory. No dataset or annotation is changed by preparation.
The preparation marker records interpreter/runtime versions and cached artifact
paths, sizes, and modification times. Deleted or changed artifacts require
preparation again. A labeling job does not deliberately initiate a weights download;
its adapter requires a valid preparation marker before loading the SDK. The SDK
still performs its own cache and authorization checks on initialization.

Project preferences contain the selected model reference and prompts. Each run
snapshots the definition version, parameters, class bindings, base runtime, and
provider preparation metadata. Imported checkpoints retain content hashes; SAM 3
cache records use file metadata, not a cryptographic content guarantee. Changed
runtime/cache records prevent resuming an old run and require a new one.

## Ollama vision models

The catalog includes curated local Ollama choices: `qwen3-vl:4b`,
`qwen3-vl:8b`, and `gemma3:4b`. Ollama manages model files and GPU execution; the
InoLabel catalog only exposes approved model tags. `GET /api/tags` discovers
installed models and `POST /api/pull` streams download progress. No public model
registry enumeration endpoint is used. The local default is
`http://127.0.0.1:11434`; an optional `OLLAMA_HOST` must resolve to loopback.

The model form provides one image instruction and descriptions bound to project
classes. The adapter sends the image and a JSON schema to Ollama's chat endpoint,
then validates class names, normalized coordinates, dimensions, and scores before
creating review proposals. Coordinates are requested in the 0–1000 range and
converted to pixels. This is generative grounding, not a deterministic object
detector; evaluate outputs on representative project images before relying on them.
The API download runs in a background thread and reports Ollama's byte progress.
The Ollama service continues the download if the panel closes.

## Image resolution and preprocessing policy

Keep source images and their dataset files unchanged. Image transforms belong to
the selected model adapter at inference time; the shared prediction contract uses
the original image, and adapters must map any resized, padded, or tiled prediction
back to original-image pixel coordinates before creating proposals.

Resolution is a per-image resource decision, not a dataset-wide normalization
step. Vision-language models may turn more image pixels into more visual tokens,
which increases context and GPU-memory use. A dataset batch still sends one image
per model request; images do not share a single context window. The Qwen3-VL
processor supports minimum and maximum pixel budgets, while traditional detectors
such as YOLO use their model-specific input size and letterbox preprocessing.

The Ollama adapter preserves the source image and resizes only the in-memory
inference copy when it exceeds 1.5 million pixels. Resizing preserves aspect ratio
and uses area interpolation. The request declares the resized dimensions, while
normalized coordinates are mapped to the original image dimensions when proposals
are created. The adapter uses `num_ctx=8192` and `num_predict=3072`, and reports a
context/generation-limit error when Ollama marks a response as truncated, including
when the partial content cannot be parsed as JSON.

This pixel budget reduces visual detail and may make very small targets harder to
detect. It is a model-specific resource tradeoff, not a dataset-wide normalization
step: source files and existing annotations are never rewritten. For large images
with small objects, overlapping tiles and box merging may be preferable; any tile
coordinates and offsets must map back to original-image pixels. Evaluate the chosen
budget against the project's smallest targets before relying on generated proposals.

## Extension points

```text
app/autolabeling/model_catalog/
  schemas.py                  # definition metadata and ModelInputs contract
  prompt_inputs.py            # reusable project-bound class descriptions
  registry.py                 # explicit integration registrations
  configuration.py            # shared reference/class-binding validation
  settings.py                 # local setup, preparation hooks, and dependency diagnostics
  definitions/
    yolo.py
    sam3.py
    ollama.py
app/autolabeling/adapters/
  sam3.py                     # polygon-to-box translation and worker lifecycle
  ollama.py                   # local Ollama chat and validated box output
app/autolabeling/runtimes/
  roboflow.py                 # setup, preparation, cache checks, subprocess client
  roboflow_worker.py          # standalone optional-runtime SDK worker
  ollama.py                    # local Ollama inventory and pull jobs
frontend/src/features/autolabeling/model-config/
  ModelSourceSelector.tsx
  ImportedModelSection.tsx
  FoundationModelSection.tsx
  ModelConfigForm.tsx
  ModelSetupDialog.tsx
  controls/ClassPromptsControl.tsx
  schema.ts
```

The backend definition is the single source for tasks, input JSON Schema, labels,
bounds, defaults, custom control hints, score meaning, and setup dependencies.
The frontend does not maintain a separate model-name list or switch on SAM/DINO/GPT.

## Add another model

1. Define a typed input class inheriting `ModelInputs`. Use `ClassPromptInputs`
   when concepts are explicitly bound to project classes. Otherwise implement
   `project_classes()` and, where meaningful, `proposal_prompt(class_name)`.
   Unknown fields and non-finite numeric values are rejected by default.
2. Declare a `ModelDefinition` with a stable ID, adapter ID, supported tasks,
   strategy, source, schema version, typed inputs, adapter factory, score meaning,
   dependencies, and documentation link. Optional trusted `runtime_status` and
   `preparation` hooks provide readiness snapshots and explicit model preparation
   without model-name branches in the panel or API. Add it to the registry.
3. Implement the adapter. For the current detection pipeline:
   - Constructor accepts a resolved checkpoint path, or an empty reference for
     integrations declared with `requires_checkpoint=False`.
   - `inspect()` returns the checkpoint vocabulary, or `{}` for prompt-based models.
   - `predict(image, config, classes)` receives an original BGR NumPy image and
     returns `(project_category_id, [x, y, width, height], score)` entries.
   - Implement `close()` when the adapter owns runtime resources. Jobs call it
     after success, cancellation, or failure.
   - Bind outputs explicitly to project classes. Never guess a class by numeric
     position or mutate project annotation state from a provider adapter.
   - Return finite coordinates/scores and positive box dimensions. Convert native
     coordinates, resizing, padding, and image formats inside the adapter.
4. Add adapter contract tests plus schema/catalog tests. A provider integration
   using different text/numeric inputs should work without changes to the job loop
   or panel. The test suite includes such an integration.
5. Increment the definition's schema version for incompatible parameter/behavior
   changes. Interrupted jobs cannot resume with a different definition version.

For future remote providers, declare their SDK packages instead of Ultralytics,
set `requires_checkpoint=False`, and use backend environment/secret references.
`required_environment` can describe missing server variables without exposing
values. Never declare credentials as project input parameters. Remote data consent,
usage limits, and provider-specific execution still require implementation.

Task declarations must reflect actual validated output capabilities. Adding a
vision-language model does not automatically make it a detector. New annotation
output tasks need the appropriate proposal/gateway support, beyond catalog registration.

## Form rendering

`ModelConfigForm` supports the common schema subset used by these integrations:
text, numeric/integer, boolean, enum, nested object fields, and local `$defs`
references. It uses backend titles, descriptions, defaults, bounds, and lengths.
The backend remains the authoritative validator.

A specialized widget is selected by `x-control`. The initial `class-prompts` widget
lets users select project classes and edit their descriptions. Register new controls
in the form's control registry only for inputs not covered by existing controls,
such as future canvas prompts or image exemplars. Do not embed model-specific
conditions in the main Autolabeling panel or arbitrary executable UI in the schema.

Configurations are held separately per model while switching sections, and reset
between projects. Pending review and historical runs are independent of the active
configuration form. Foundation scores are shown as model scores, not calibrated
YOLO probabilities.

## Validation boundaries

Automated coverage includes catalog discovery without SDK imports, registering a
new integration, typed validation, task filtering, setup isolation, legacy YOLO
compatibility, SAM prompt/class association, polygon bounds, worker lifecycle and
credential redaction, preparation invalidation, shared-job execution, model-switch draft preservation, and schema-driven
server rendering. SDK-call contract tests use fake responses; subprocess tests verify
the JSON protocol without downloading a model.

Real SAM 3 inference and quality evaluation still require a configured Roboflow
key, authorized model access, downloaded weights, and suitable hardware. They have
not been performed in this delivery.

Sources:

- [Roboflow SAM 3 weights and local Inference guide](https://roboflow.com/blog/download-sam-3-weights)
- [Roboflow SAM 3 reference](https://docs.roboflow.com/models/supported-models/sam3)
- [Pinned Inference SDK release](https://pypi.org/project/inference-gpu/1.1.2/)
- [Qwen3-VL image pixel budgets and preprocessing](https://github.com/QwenLM/Qwen3-VL)
- [Ultralytics prediction image size and letterbox behavior](https://docs.ultralytics.com/modes/predict)
- [Ollama Modelfile context and generation parameters](https://docs.ollama.com/modelfile)
