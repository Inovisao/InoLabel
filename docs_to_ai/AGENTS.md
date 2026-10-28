# InoLabel implementation rules

These rules apply to every change in this repository. The structure described
below already exists; apply the maintenance rules to new changes without
requiring a general rewrite of existing code.

## Before making changes

- Read the affected flow, its tests, and the relevant documentation.
- Check `git status` and the current diff. Preserve user changes and previous
  work; do not revert, reformat, or replace entire files unnecessarily.
- Look for existing functions, components, types, and validation before adding new ones.
- Keep changes scoped. Separate broad refactoring from targeted fixes.
- Do not change public contracts, file formats, or dependencies for convenience.

## Organization and responsibilities

| Location | Responsibility |
| --- | --- |
| `main.py`, `api_server.py` | Application/API startup and execution |
| `app/api/<module>/router.py` | Routes, HTTP input, and delegation to services |
| `app/api/<module>/schemas.py` | Contracts and structural validation with Pydantic |
| `app/api/<module>/service.py` | Use cases and coordination of module rules |
| `app/api/common/` | Shared API errors and contracts |
| `app/core/` | Cross-cutting resources: sessions, paths, state, and detector |
| `app/annotation/core/` | Transformations and shared annotation/export rules |
| `app/annotation/infrastructure/` | Annotation persistence and export |
| `app/annotation_obb/`, `app/annotation_keypoint/` | OBB and pose rules |
| `app/classification/dataset/` | Classification data organization and transfers |
| `tracker/` | Tracking algorithms |
| `frontend/src/features/<feature>/` | Feature components, state, and behavior |
| `frontend/src/shared/` | API, UI, sessions, and layout reused across features |
| `utils/`, `scripts/` | Standalone utilities and build automation |
| `tests/`, `frontend/tests/` | Behavior and regression tests |

- Keep specific files inside their module. Move code into shared modules only
  when it has a common use and a clear responsibility.
- Avoid generic modules such as `helpers.py` that accumulate unrelated functions.
- Preserve the separation of transport, rules, geometry, and file access.
  Do not put business rules in routes or presentation components.
- Use existing services and `DomainError` for business rule violations; keep
  translation into HTTP responses in the API layer.
- Follow the existing annotation state slices and types in the frontend.
  Avoid duplicating derived state or creating another source of truth.

## Clean code and comments

- Use names that express intent and functions with clear responsibilities.
- Follow the module's language and style. Use English identifiers and types
  consistent with existing contracts. Avoid unjustified `Any` and casts.
- Prefer composition and small functions over premature generic abstractions.
  Do not create classes or layers that only forward calls without a purpose.
- Centralize common rules; preserve rules specific to each annotation mode.
- Validate input at boundaries and handle expected errors explicitly.
  Do not swallow broad exceptions or present failures as successful operations.
- Comments should explain decisions, constraints, or non-obvious risks. Avoid
  narrating each line, large decorative headers, and change histories.
- Keep docstrings concise. Extensive architecture, installation, and usage
  explanations belong in documentation. Preserve comments explaining real risks.
- Do not leave dead code, commented-out blocks, debug prints, or duplication.

## Required reuse where applicable

- Label paths: `app/core/label_paths.py`; preserve subdirectories and ambiguous
  name detection instead of reconstructing paths from file stems alone.
- Dataset splitting and YOLO labels: `app/annotation/core/export/`.
- Augmentation: `app/annotation/core/augmentation/` and the pose-specific adapter.
- OBB geometry: `app/annotation_obb/geometry/obb_geometry.py`.
- Export destinations: `app/annotation/infrastructure/export/export_dir.py`.
- YOLO job planning and writing: `app/annotation/infrastructure/export/yolo_jobs.py`.
- State reading/writing: persistence modules and `app/core/project_state/`.
- Frontend HTTP requests: `frontend/src/shared/api/client.ts` and existing contracts.
- Inference: the `app/core/detector.py` wrapper. Preserve lazy model loading;
  opening the interface must not load YOLO/PyTorch in advance.
- Autolabeling integrations: register definitions and typed inputs in
  `app/autolabeling/model_catalog/`; reuse shared jobs and proposal review.
  Render model fields from the catalog schema instead of branching on model names
  in the panel. Keep incompatible optional SDKs in isolated runtimes.

## Data preservation and overwrite prevention

- Never delete or recreate an arbitrary destination to simplify an export.
  Use directory protection with the `.inolabel_export` marker.
- Validate resolved paths, destination boundaries, and collisions before writing.
  Do not allow input paths to escape the output directory.
- Preserve source datasets. Distinguish reading, copying, moving, and replacing.
- Before modifying existing annotations, load persisted state through the module's
  flow, including `ensure_loaded_from_disk` where applicable.
- Reuse existing atomic writes, locks, and flush operations. A failure must not
  leave a valid file partially overwritten or discard concurrent updates.
- Preserve IDs, class order, references between files, and saved state compatibility.
  Format changes require migration or explicit compatibility handling.
- Do not commit models, datasets, outputs, secrets, personal settings, caches,
  or builds. Respect `.gitignore` and exclude files generated by tests.

## Documentation and dependencies

- Keep maintained documentation in English, including new sections and updates.
  Preserve literal paths, commands, identifiers, and quoted application messages.
- Update the README when installation, execution, commands, features,
  requirements, exports, or user-visible behavior change.
- Update these rules when architecture or maintenance conventions change.
  Document the final state without presenting planned features as completed.
- Maintained documentation must live in tracked paths. `docs/` and `docs_agents/`
  are currently ignored; do not put official documentation there without
  deliberately changing that policy.
- Declare new direct dependencies in the appropriate file. Python libraries go
  in requirements files; Node dependencies go in `frontend/package.json`, with
  the lockfile updated by the tool. Never edit the lockfile manually.
- Preserve existing pins unless a change is justified. Account for Python 3.9,
  used by CI, and Node 22, used by frontend CI. Do not use language features
  incompatible with supported environments without updating policy and validation.
- Do not add dependencies for functionality already provided by the project or
  the standard library. Separate runtime, development, and build dependencies.

## Validation and delivery

- For logic, contract, or persistence fixes, add or update tests that reproduce
  the problem and verify expected behavior, including relevant failure cases.
- Simple text/documentation changes do not require artificial tests.
- Backend: run affected tests with `python -m pytest -q tests/<file>.py`.
  For cross-cutting changes, run `python -m pytest -q tests` in a prepared environment.
- Frontend: inside `frontend/`, run `npx tsc --noEmit`, `npm test`, and `npm run build`
  for code changes. Use `npm ci` to install from the lockfile.
- Startup/distribution: check the API, compiled interface, and assets;
  a successful `/health` response alone does not prove that the interface works.
- Review `git diff --check` and the final diff. Exclude accidental changes.
- At delivery, describe the changed behavior, checks performed, and concrete
  limitations. Distinguish passing tests from checks blocked by the environment.
