---
last_mapped_commit: af6f39f6d52b32e68a7d38ed4a1b747fd1283f01
---
# Testing Patterns

**Analysis Date:** 2026-06-02

## Test Framework

**Runner:**
- Python tests are written with `unittest` from the standard library: `tests/test_session_config.py`, `tests/test_dataset_export.py`, `tests/test_class_removal.py`, `tests/test_tracker_matching_fallbacks.py`.
- CI invokes pytest collection/execution with `python -m pytest -q || true` in `.github/workflows/ci.yml`; the `|| true` means Python test failures do not fail CI.
- No pytest configuration file is detected: no `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tox.ini` at the repository root.
- Frontend has no detected unit test runner. `frontend/package.json` has `dev`, `build`, `preview`, and `tauri` scripts only.

**Assertion Library:**
- Python uses `unittest.TestCase` assertions: `assertEqual`, `assertTrue`, `assertFalse`, `assertIsNone`, `assertAlmostEqual`, `assertRaises`, and `assertGreaterEqual` in `tests/`.
- NumPy assertions are not the dominant pattern; tests use `unittest` assertions over NumPy arrays and lists, for example `tests/test_tracker_matching_fallbacks.py` and `tests/test_class_removal.py`.
- Frontend assertions are not detected because no frontend tests are present under `frontend/src/`.

**Run Commands:**
```bash
python -m unittest discover -s tests -p "test*.py"  # Run all unittest tests
python -m pytest -q                                # Run tests with pytest collection, if pytest is installed
cd frontend && npm run build                       # Type-check and build the frontend
```

## Test File Organization

**Location:**
- Python tests live in the top-level `tests/` directory and are not co-located with implementation files.
- Implementation files under test live in `app/`, `tracker/`, and `utils/`: `app/core/session.py`, `app/annotation/infrastructure/export/yolo_exporter.py`, `tracker/matching.py`, `utils/merge_yolo_splits.py`.
- No `frontend/src/**/*.test.tsx` or `frontend/src/**/*.spec.tsx` files are detected.

**Naming:**
- Use `tests/test_<feature>.py` for automated tests: `tests/test_keybinds.py`, `tests/test_output_state.py`, `tests/test_session_installer.py`.
- `tests/main_test.py` is an interactive/manual smoke script that opens video/model resources and displays OpenCV output; do not treat it as the pattern for isolated automated tests.
- Test classes use `<Subject>Test` names: `SessionConfigTest`, `SourceDiscoveryServiceTest`, `ExportYoloDatasetTest`, `TrackerMatchingFallbackTest`.
- Test methods use `test_<expected_behavior>` names: `test_normalize_class_names_removes_empty_and_duplicates`, `test_yolo_export_writes_augmented_images_and_labels_in_same_split`, `test_scipy_linear_assignment_respects_threshold`.

**Structure:**
```text
tests/
├── test_session_config.py          # Session config and source discovery unit tests
├── test_dataset_export.py          # Export, persistence, workflow, pan/zoom, merge tests
├── test_class_removal.py           # Class-removal behavior with dummy mixin host
├── test_components.py              # Tkinter component factory tests
├── test_tracker_matching_fallbacks.py
└── main_test.py                    # Manual OpenCV/YOLO smoke script
```

## Test Structure

**Suite Organization:**
```python
import tempfile
import unittest
from pathlib import Path

from app.core.session import AnnotationSessionConfig, AnnotationTaskMode


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
- Put imports at the top and keep tests readable with explicit arrangements, as in `tests/test_session_config.py` and `tests/test_dataset_export.py`.
- Use `tempfile.TemporaryDirectory()` for filesystem tests so tests do not write into repo data folders: `tests/test_session_config.py`, `tests/test_dataset_export.py`, `tests/test_session_installer.py`, `tests/test_classification_dataset.py`.
- Build small payload dictionaries inline when testing COCO/YOLO export logic: `tests/test_dataset_export.py`, `tests/test_yolo_obb_export.py`, `tests/test_class_order.py`.
- Use local dummy classes to host mixins without launching the full UI: `DummyWorkflow` in `tests/test_dataset_export.py`, `DummyClassConfig` in `tests/test_class_removal.py`, `_Stub` in `tests/test_annotation_storage_perf.py`.
- Keep GUI tests minimal and withdraw/destroy Tk roots in `setUp`/`tearDown`: `TkTestCase` in `tests/test_components.py`.
- Use `if __name__ == "__main__": unittest.main()` at the end of test modules for direct execution: most files under `tests/`.

## Mocking

**Framework:** `unittest.mock`

**Patterns:**
```python
from unittest.mock import patch


with patch("app.annotation.state.class_config.messagebox.askyesno", return_value=True):
    config.remove_class("bus")
```

**What to Mock:**
- Mock Tkinter dialogs and user confirmations instead of opening UI modals: `tests/test_class_removal.py`.
- Stub mixin host methods that produce side effects, then assert call counters or captured arguments: `tests/test_dataset_export.py`, `tests/test_class_removal.py`, `tests/test_annotation_storage_perf.py`.
- Use fake image bytes or generated NumPy/OpenCV images for export paths: `tests/test_dataset_export.py`, `tests/test_yolo_obb_export.py`.

**What NOT to Mock:**
- Do not mock pure transformation logic. Tests exercise real helpers such as `normalize_class_names` in `app/core/session.py`, `_bbox_overlaps_numpy` in `tracker/matching.py`, and `merge_yolo_splits` in `utils/merge_yolo_splits.py`.
- Do not start the full Tkinter annotation tool for unit tests. Test mixins and component factories with dummy hosts or minimal roots: `tests/test_components.py`, `tests/test_dataset_export.py`.
- Do not depend on real user datasets, model weights, or OpenCV display windows in automated tests. `tests/main_test.py` is the manual exception.

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
- Test helper factories live in the test files that use them, not in a shared fixture module: `make_detection` in `tests/test_class_removal.py`, `_make_session` in `tests/test_session_installer.py`, `_make_ann` and `_make_img` in `tests/test_annotation_storage_perf.py`.
- Filesystem fixtures are created inside `TemporaryDirectory()` blocks: `tests/test_session_config.py`, `tests/test_dataset_export.py`, `tests/test_classification_dataset.py`.
- Image fixtures are generated dynamically with `cv2.imwrite` and `np.zeros` where real encoded images matter: `tests/test_dataset_export.py`.

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
python -m coverage run -m unittest discover -s tests -p "test*.py"
python -m coverage report
```

- No coverage package is listed in `requirements.txt`.
- No coverage configuration file is detected.
- CI in `.github/workflows/ci.yml` does not collect or enforce coverage.

## Test Types

**Unit Tests:**
- Core configuration and normalization: `tests/test_session_config.py` covers `app/core/session.py` and `app/sources/discovery.py`.
- Geometry and tracker helpers: `tests/test_obb_geometry.py`, `tests/test_scale.py`, `tests/test_tracker_matching_fallbacks.py`.
- Theme and UI component factories: `tests/test_theme.py`, `tests/test_theme_compat.py`, `tests/test_palette.py`, `tests/test_components.py`.
- Keybind model/repository/action behavior: `tests/test_keybinds.py`.

**Integration Tests:**
- Filesystem export and persistence workflows use temporary directories and real file writes: `tests/test_dataset_export.py`, `tests/test_yolo_obb_export.py`, `tests/test_session_installer.py`, `tests/test_classification_dataset.py`.
- Annotation storage and rebuild behavior is tested through stub host classes over persistence/review mixins: `tests/test_annotation_storage_perf.py`.
- Model contract tests skip when optional dependencies are absent: `tests/test_model_class_mapping.py`, `tests/test_obb_tool_contract.py`.

**E2E Tests:**
- Not used for the main application.
- `.github/workflows/ci.yml` runs demo Playwright tests under `.impeccable/demo`, which is outside the app source tree.
- `tests/main_test.py` is a manual OpenCV/YOLO smoke script and requires local `tests/videos/` and `tests/yolo26m.pt`.

## Common Patterns

**Async Testing:**
```typescript
// No frontend async test pattern is currently present.
// Frontend async behavior lives in Zustand stores such as frontend/src/stores/session.ts.
```

**Error Testing:**
```python
def test_session_requires_at_least_one_class(self):
    with self.assertRaises(ValueError):
        AnnotationSessionConfig(
            mode=AnnotationTaskMode.TRACKING,
            data_root=Path("images"),
            weights_path=Path("model.pt"),
            target_classes=("",),
        )
```

**Filesystem Testing:**
```python
with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_path = Path(tmp_dir)
    source_images_dir = tmp_path / "images"
    dataset_root = tmp_path / "yolo_dataset"
    source_images_dir.mkdir(parents=True, exist_ok=True)
```

**Optional Dependency Testing:**
- Skip contract tests when heavyweight optional imports are unavailable: `tests/test_model_class_mapping.py` and `tests/test_obb_tool_contract.py` use `unittest.SkipTest`.

**GUI Testing:**
- Use a withdrawn root and destroy it in teardown for component tests: `tests/test_components.py`.

---

*Testing analysis: 2026-06-02*
