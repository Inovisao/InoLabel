# Testing Patterns

**Analysis Date:** 2026-05-29

## Test Framework

**Runner:**
- Python tests use the standard library `unittest` framework with test modules under `tests/`: `tests/test_session_config.py`, `tests/test_dataset_export.py`, `tests/test_keybinds.py`.
- Tests are compatible with direct module execution because each file ends with `if __name__ == "__main__": unittest.main()`: `tests/test_session_config.py`, `tests/test_classification_dataset.py`, `tests/test_obb_geometry.py`.
- A `.pytest_cache/` directory exists, so pytest can discover and run the `unittest` suites, but no `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tox.ini` test configuration is present.
- Frontend has no test runner configured. `frontend/package.json` defines `dev`, `build`, `lint`, and `preview`, but no `test` script.

**Assertion Library:**
- Python tests primarily use `unittest.TestCase` assertions: `self.assertEqual`, `self.assertTrue`, `self.assertFalse`, `self.assertIsNone`, `self.assertRaises` in `tests/test_session_config.py`, `tests/test_keybinds.py`, and `tests/test_classification_dataset.py`.
- Numeric array comparisons use NumPy testing helpers where precision matters: `np.testing.assert_allclose` in `tests/test_obb_geometry.py`.
- No JavaScript/TypeScript assertion library is configured in `frontend/package.json`.

**Run Commands:**
```bash
python -m unittest discover -s tests -p "test_*.py"  # Run all Python tests
python -m unittest tests.test_session_config          # Run one Python test module
cd frontend && npm run lint                           # Run frontend lint checks
cd frontend && npm run build                          # Type-check and build frontend
```

## Test File Organization

**Location:**
- Python tests live in the top-level `tests/` directory and import production code by absolute `backend.*` paths: `tests/test_session_config.py`, `tests/test_dataset_export.py`, `tests/test_classification_dataset.py`.
- There are no co-located frontend tests under `frontend/src/` and no test directory under `frontend/`.

**Naming:**
- Test files use `test_<feature>.py`: `tests/test_output_state.py`, `tests/test_class_order.py`, `tests/test_yolo_obb_export.py`.
- Test case classes use `<Feature>Test` names: `SessionConfigTest` in `tests/test_session_config.py`, `ClassificationDatasetTest` in `tests/test_classification_dataset.py`, `OBBGeometryTest` in `tests/test_obb_geometry.py`.
- Test methods use descriptive `test_<expected_behavior>` names: `test_create_new_output_dir_avoids_same_minute_conflicts` in `tests/test_output_state.py`, `test_remove_class_purges_category_annotations_and_detection_caches` in `tests/test_class_removal.py`.

**Structure:**
```text
tests/
├── test_session_config.py          # session config and source discovery
├── test_output_state.py            # output state naming/loading/filtering
├── test_dataset_export.py          # YOLO export, persistence mixins, workflow behavior
├── test_classification_dataset.py  # classification state and file operations
├── test_keybinds.py                # keybinding maps and repository behavior
├── test_obb_geometry.py            # oriented bounding box geometry
└── test_yolo_obb_export.py         # YOLO OBB export output
```

## Test Structure

**Suite Organization:**
```python
import tempfile
import unittest
from pathlib import Path

from backend.core.session import AnnotationSessionConfig, AnnotationTaskMode


class SessionConfigTest(unittest.TestCase):
    def test_session_config_keeps_mode_and_paths(self):
        config = AnnotationSessionConfig(
            mode=AnnotationTaskMode.DETECTION,
            data_root=Path("images"),
            weights_path=Path("model.pt"),
            target_classes=("Documento",),
        )

        self.assertFalse(config.tracking_enabled)
        self.assertEqual(config.mode, AnnotationTaskMode.DETECTION)
```

**Patterns:**
- Keep each behavior in its own `test_*` method and build data inline near the assertion: `tests/test_output_state.py`, `tests/test_classification_dataset.py`.
- Use `tempfile.TemporaryDirectory()` for filesystem tests so test data is isolated and removed automatically: `tests/test_dataset_export.py`, `tests/test_keybinds.py`, `tests/test_startup_cache.py`.
- Use nested dummy classes to exercise mixins without constructing the full UI/runtime stack: `DummyWorkflow` in `tests/test_dataset_export.py`, `DummyClassConfig` in `tests/test_class_removal.py`, `DummyModelClassMapper` in `tests/test_model_class_mapping.py`.
- Use direct method calls over API/client tests for backend behavior; no FastAPI `TestClient` tests are present.
- Keep assertions explicit and state-focused. Tests check generated files, returned reports, dataclass fields, and mutated caches directly: `tests/test_dataset_export.py`, `tests/test_classification_dataset.py`, `tests/test_class_removal.py`.
- End each test module with `unittest.main()` for direct execution: all inspected files under `tests/`.

## Mocking

**Framework:** No external mocking framework is used. Tests use hand-written dummy classes, temporary files, and optional dependency skips.

**Patterns:**
```python
class DummyWorkflow(WorkflowActionsMixin):
    def __init__(self):
        self.current_frame = np.zeros((16, 16, 3), dtype=np.uint8)
        self.current_detections = []
        self.manual_detections = []
        self.write_calls = 0

    def write_annotations(self):
        self.write_calls += 1
```

**What to Mock:**
- Mock UI/runtime dependencies with local dummy classes when testing mixins: `WorkflowActionsMixin` in `tests/test_dataset_export.py`, `ClassConfigMixin` in `tests/test_class_removal.py`.
- Mock file inputs with temporary directories, small text files, JSON payloads, and generated images: `tests/test_output_state.py`, `tests/test_classification_dataset.py`, `tests/test_dataset_export.py`.
- Mock optional ML/runtime dependencies by skipping tests if imports are unavailable: `setUpClass` in `tests/test_model_class_mapping.py`.

**What NOT to Mock:**
- Do not mock pure geometry math; test real NumPy outputs directly: `tests/test_obb_geometry.py`.
- Do not mock filesystem writes for export/state functions; assert actual files and directories in a temporary root: `tests/test_dataset_export.py`, `tests/test_classification_dataset.py`, `tests/test_startup_cache.py`.
- Do not mock class/order remapping state when the test purpose is mutation behavior; use dummy objects with realistic attributes and inspect the mutated structures: `tests/test_class_removal.py`.

## Fixtures and Factories

**Test Data:**
```python
def make_detection(category_id: int) -> Detection:
    return Detection(
        original_bbox=np.array([1, 2, 10, 20], dtype=np.float32),
        warp_bbox=None,
        confidence=1.0,
        category_id=category_id,
        track_id=None,
        source="manual",
        internal_id=None,
    )
```

**Location:**
- Factories are local to the test module that needs them, not shared globally: `make_detection` in `tests/test_class_removal.py`, `_write_annotations` in `tests/test_output_state.py`, `_make` in `tests/test_keybinds.py`.
- JSON payload fixtures are inline dictionaries inside test methods: `tests/test_dataset_export.py`, `tests/test_classification_dataset.py`, `tests/test_output_state.py`.
- Image fixtures are generated with `Path.write_bytes` for placeholder files or `cv2.imwrite` plus NumPy arrays when image decoding is part of the behavior: `tests/test_dataset_export.py`.

## Coverage

**Requirements:** Not enforced. No `.coveragerc`, coverage configuration, or coverage script is detected.

**View Coverage:**
```bash
python -m coverage run -m unittest discover -s tests -p "test_*.py"  # Requires coverage installed separately
python -m coverage report
```

Coverage tooling is not listed in `requirements.txt`; add it intentionally before depending on these commands in CI.

## Test Types

**Unit Tests:**
- Pure helper and model tests cover session config, geometry, class name normalization, keybind maps, state naming, and output state selection: `tests/test_session_config.py`, `tests/test_obb_geometry.py`, `tests/test_keybinds.py`, `tests/test_output_state.py`.
- Mixin unit tests use dummy classes to exercise behavior without launching UI or FastAPI: `tests/test_dataset_export.py`, `tests/test_class_removal.py`.

**Integration Tests:**
- Filesystem integration tests cover export outputs, labels, generated YAML, state persistence, and classification dataset file movement/copying: `tests/test_dataset_export.py`, `tests/test_classification_dataset.py`, `tests/test_yolo_obb_export.py`.
- Optional model mapping behavior is tested through import-gated dummy classes: `tests/test_model_class_mapping.py`.

**E2E Tests:**
- Not used. No Playwright, Cypress, Selenium, browser tests, or desktop `pywebview` automation tests are configured in `frontend/package.json`, `requirements.txt`, or `tests/`.

**Frontend Tests:**
- Not configured. Validate frontend changes with `cd frontend && npm run lint` and `cd frontend && npm run build` because those are the available scripts in `frontend/package.json`.

**API Tests:**
- Not configured. Backend API routers in `backend/api/` have no FastAPI `TestClient` tests under `tests/`.

## Common Patterns

**Async Testing:**
```python
# No async test runner pattern is present.
# FastAPI async endpoints in backend/api/*.py are tested indirectly through domain helpers, if at all.
```

Use synchronous unit tests for domain helpers unless adding an API test around an async FastAPI endpoint. If API tests are added, place them under `tests/test_<router>_api.py` and keep them aligned with `backend/api/session.py`, `backend/api/frame.py`, and `backend/api/export.py`.

**Error Testing:**
```python
with self.assertRaises(ValueError):
    load_state(state_path)
```

- Use `self.assertRaises` for expected domain errors: `tests/test_session_config.py`, `tests/test_classification_dataset.py`.
- Use skip tests for missing optional dependencies instead of failing the whole suite: `unittest.SkipTest` in `tests/test_model_class_mapping.py`.
- Use malformed JSON and incompatible payloads to validate defensive loaders: `tests/test_startup_cache.py`, `tests/test_classification_dataset.py`, `tests/test_keybinds.py`.

**Filesystem Assertions:**
```python
with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    output = root / "output"
    output.mkdir()

    self.assertTrue((output / "ok").is_dir())
```

- Always build filesystem tests inside `TemporaryDirectory`: `tests/test_classification_dataset.py`, `tests/test_output_state.py`, `tests/test_dataset_export.py`.
- Assert both returned report values and on-disk artifacts for export behavior: `tests/test_dataset_export.py`, `tests/test_yolo_obb_export.py`.

**Numerical Assertions:**
```python
np.testing.assert_allclose(points, expected, atol=1e-4)
```

- Use `assertAlmostEqual` for scalar floating point values: `tests/test_obb_geometry.py`.
- Use NumPy testing helpers for arrays: `tests/test_obb_geometry.py`.

**Adding New Tests:**
- Add backend/domain tests as `tests/test_<feature>.py` using `unittest.TestCase`.
- Prefer temporary directories and inline payloads over committed fixtures unless the fixture is too large or shared by several tests.
- Keep test imports absolute from `backend.*`, matching `tests/test_session_config.py` and `tests/test_dataset_export.py`.
- Add frontend tests only after adding a test runner and script to `frontend/package.json`; until then, use lint/build as frontend verification.
- Add API tests with FastAPI `TestClient` only when route behavior matters beyond the underlying service/domain helper.

---

*Testing analysis: 2026-05-29*
