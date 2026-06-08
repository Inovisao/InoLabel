# Testing Patterns

**Analysis Date:** 2026-06-08

## Test Framework

**Runner:**
- Python: pytest is the intended repository runner, invoked by `.github/workflows/ci.yml` with `python -m pytest -q`.
- Python tests also use `unittest.TestCase` heavily; pytest collects these classes from `tests/test_*.py`.
- Frontend app: no Vitest/Jest/Playwright test config is detected under `frontend/`.
- Demo accessibility island: plain Node script using Playwright in `.impeccable/demo/tests/accessibility.test.js`.
- Config: Not detected for pytest (`pytest.ini`, `pyproject.toml`, `setup.cfg`, and `tox.ini` are absent).

**Assertion Library:**
- Python: built-in `assert` for pytest-style tests in `tests/test_api_contract.py`, `tests/test_session_start_audit.py`, and `tests/test_lab_notebook_design_contract.py`.
- Python: `unittest.TestCase` assertions for class-based tests in `tests/test_dataset_export.py`, `tests/test_export_improvements.py`, `tests/test_keybinds.py`, and `tests/test_class_removal.py`.
- API integration: `fastapi.testclient.TestClient` in `tests/test_api_contract.py`, `tests/test_session_start_audit.py`, and `tests/test_export_improvements.py`.
- Demo browser test: manual `throw new Error(...)` checks with Playwright APIs in `.impeccable/demo/tests/accessibility.test.js`.

**Run Commands:**
```bash
python -m pytest -q              # Run Python test suite from repository root
npm run build                    # Type-check and build frontend from frontend/
npm test                         # Run demo Playwright checks from .impeccable/demo/
```

## Test File Organization

**Location:**
- Python tests are centralized in `tests/`.
- Tests target source areas by feature name: `tests/test_api_contract.py` for API boundaries, `tests/test_session_start_audit.py` for session start behavior, `tests/test_export_audit.py` and `tests/test_export_improvements.py` for export behavior, `tests/test_keybinds.py` for keybinding domain behavior.
- Frontend design/layout contracts are Python tests that inspect source files directly in `frontend/src`, especially `tests/test_lab_notebook_design_contract.py`.
- Demo accessibility checks live outside the application test suite in `.impeccable/demo/tests/accessibility.test.js`.

**Naming:**
- Use `test_*.py` for Python test files.
- Use `test_*` for pytest functions and `Test*` or domain-specific `*Test` for `unittest.TestCase` classes.
- Use helper names prefixed with `_` inside tests: `_client` in `tests/test_api_contract.py`, `_start` in `tests/test_session_start_audit.py`, `_make_payload` in `tests/test_export_improvements.py`.

**Structure:**
```text
tests/
├── test_api_contract.py              # API import and endpoint contracts
├── test_session_start_audit.py       # pytest fixture-driven session audit
├── test_export_audit.py              # export correctness and edge cases
├── test_export_improvements.py       # unittest regression suites
├── test_dataset_export.py            # dataset export integration/unit tests
└── test_*.py                         # focused domain tests

.impeccable/demo/tests/
└── accessibility.test.js             # standalone Playwright browser checks
```

## Test Structure

**Suite Organization:**
```python
# tests/test_session_start_audit.py
@pytest.fixture(autouse=True)
def _reset_state():
    from app.api import state as _state
    _state.reset_state()
    yield
    _state.reset_state()

@pytest.fixture
def client() -> TestClient:
    from app.api.main import app
    return TestClient(app)

class TestSchemaClasses:
    def test_duplicate_classes_are_deduplicated(self):
        from app.api.schemas import SessionStartRequest
        req = SessionStartRequest(
            mode="detection", classes=["dog", "cat", "dog"], data_path="/tmp"
        )
        assert req.classes == ["dog", "cat"]
```

```python
# tests/test_export_improvements.py
class TestNormalizeSplitRatios(unittest.TestCase):
    def _call(self, *args):
        from app.annotation.core.export.split_service import normalize_split_ratios
        return normalize_split_ratios(*args)

    def test_negative_ratio_raises(self):
        with self.assertRaises(ValueError):
            self._call((-0.1, 0.5, 0.6))
```

**Patterns:**
- Prefer pytest fixtures for shared API integration state and temp directories in large endpoint suites (`tests/test_session_start_audit.py`).
- Use `unittest.TestCase` when tests already group behavior around a class or use `setUp`/`tearDown`, as in `tests/test_components.py`, `tests/test_annotation_storage_perf.py`, and `tests/test_export_improvements.py`.
- Reset mutable in-process API state before API tests. Use `app.api.state.reset_state()` in fixtures or test setup.
- Build local fake files with `tmp_path` or `tempfile.TemporaryDirectory()` rather than depending on repository data.
- Import heavyweight application modules inside tests or helpers when avoiding import-time side effects matters. `tests/test_api_contract.py` imports `app.api.main` inside `_client()`.

## Mocking

**Framework:** `unittest.mock.patch`; pytest `monkeypatch`; ad hoc dummy classes.

**Patterns:**
```python
# tests/test_class_removal.py
with patch("app.annotation.state.class_config.messagebox.askyesno", return_value=True):
    config.remove_class("bus")
```

```python
# tests/test_export_improvements.py
captured = io.StringIO()
with patch("sys.stdout", captured):
    export_yolo_no_split(payload, src, dataset_root)
assert "[AVISO]" in captured.getvalue()
```

```python
# tests/test_api_contract.py
def test_keybinds_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("INOLABEL_LOCAL_DIR", str(tmp_path))
    from app.api.routes import keybinds
    keybinds.KEYBINDS_PATH = tmp_path / "keybinds.json"
```

**What to Mock:**
- User confirmations and UI dialogs in Tkinter-facing logic, as in `tests/test_class_removal.py`.
- Standard output when asserting CLI/Tk warning text, as in `tests/test_export_improvements.py`.
- Environment variables and module-level paths when isolating filesystem writes, as in `tests/test_api_contract.py`.
- Runtime collaborators with small in-test dummy classes when testing mixins, as in `tests/test_class_removal.py`.

**What NOT to Mock:**
- Do not mock FastAPI route execution for API contract tests; use `TestClient` against `app.api.main`.
- Do not mock filesystem behavior for export and session tests when real temp files can verify path handling. Use `tmp_path` or `TemporaryDirectory`.
- Do not mock pure domain helpers such as `normalize_class_names`, `normalize_split_ratios`, or YOLO label formatting; call them directly.

## Fixtures and Factories

**Test Data:**
```python
# tests/test_session_start_audit.py
@pytest.fixture
def img_dir(tmp_path: Path) -> Path:
    data = tmp_path / "dataset"
    data.mkdir()
    (data / "img_a.jpg").write_bytes(b"\xff\xd8\xff")
    (data / "img_b.png").write_bytes(b"\x89PNG\r\n")
    return data
```

```python
# tests/test_class_removal.py
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
- Fixtures are local to the test module that uses them; no shared `tests/conftest.py` is detected.
- Small factories live in the test module: `make_detection` in `tests/test_class_removal.py`, `_make_ann` and `_make_img` in `tests/test_annotation_storage_perf.py`, `_make_payload` in `tests/test_export_improvements.py`.
- Temporary source images and dataset folders are generated inside tests with OpenCV, bytes stubs, or text files in `tests/test_dataset_export.py`, `tests/test_export_audit.py`, and `tests/test_session_start_audit.py`.

## Coverage

**Requirements:** None enforced. No coverage configuration or CI coverage gate is detected.

**View Coverage:**
```bash
python -m pytest --cov=app --cov=tracker --cov=utils
```

`pytest-cov` is not listed in `requirements.txt`; install it before using the coverage command.

## Test Types

**Unit Tests:**
- Pure helper tests cover geometry, export math, palettes, startup cache, session config, and keybinds: `tests/test_obb_geometry.py`, `tests/test_yolo_obb_export.py`, `tests/test_palette.py`, `tests/test_startup_cache.py`, `tests/test_session_config.py`, `tests/test_keybinds.py`.
- Use direct imports and precise assertions for these tests.

**Integration Tests:**
- API integration tests use `TestClient` and real temporary paths in `tests/test_api_contract.py` and `tests/test_session_start_audit.py`.
- Export integration tests create temporary datasets and assert emitted files/labels in `tests/test_dataset_export.py`, `tests/test_export_audit.py`, and `tests/test_export_improvements.py`.
- Tkinter component tests instantiate widgets in `tests/test_components.py`; these require a display-capable environment.

**E2E Tests:**
- No E2E tests are detected for the production `frontend/` app.
- `.impeccable/demo/tests/accessibility.test.js` launches Chromium against a local static demo server and checks keyboard menu behavior, tooltip visibility, modal focus trap, and Escape close behavior.

## Common Patterns

**Async Testing:**
```python
# app/api/routes/session.py exposes async start_session, but tests call it through TestClient
response = client.post("/api/session/start", json=start_body)
assert response.status_code == 200
```

- Prefer `TestClient` for FastAPI async routes rather than writing explicit event-loop tests.
- For frontend async UI behavior, no app-level tests are detected; add Vitest/React Testing Library or Playwright config before adding frontend test files.

**Error Testing:**
```python
# tests/test_session_start_audit.py
with pytest.raises(Exception, match="(?i)classe"):
    SessionStartRequest(mode="detection", classes=[], data_path="/tmp")
```

```python
# tests/test_api_contract.py
response = _client().post("/api/session/validate-path", json={"path": "Z:/missing/inolabel/path"})
assert response.status_code == 422
assert response.json()["valid"] is False
```

```python
# tests/test_export_improvements.py
with self.assertRaises((ValueError, TypeError)):
    self._call((0.5, 0.5))
```

---

*Testing analysis: 2026-06-08*
