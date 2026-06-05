"""
Comprehensive audit tests for the annotation session start flow.

Coverage matrix
───────────────
A) Schema unit tests          — validators, normalization, edge cases
B) Integration happy path     — all modes, file discovery, output creation
C) Integration error path     — every 422 case documented
D) Regression tests           — one test per bug fixed; named for the root cause
E) Session state & lifecycle  — isolation, cleanup, status endpoint
F) Metadata file (.inolabel.json)
G) Projects endpoint
H) Edge cases                 — unicode, spaces, long names, boundary navigation
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_state():
    """Isolate every test: wipe in-process state before and after."""
    from app.api import state as _state

    _state.reset_state()
    yield
    _state.reset_state()


@pytest.fixture
def client() -> TestClient:
    from app.api.main import app

    return TestClient(app)


@pytest.fixture
def img_dir(tmp_path: Path) -> Path:
    """Dataset directory with two image stubs (jpg + png)."""
    data = tmp_path / "dataset"
    data.mkdir()
    (data / "img_a.jpg").write_bytes(b"\xff\xd8\xff")
    (data / "img_b.png").write_bytes(b"\x89PNG\r\n")
    return data


@pytest.fixture
def out_dir(tmp_path: Path) -> Path:
    """Separate output directory (not yet created — session must create it)."""
    return tmp_path / "output"


@pytest.fixture
def start_body(img_dir: Path, out_dir: Path) -> dict:
    return {
        "mode": "detection",
        "data_path": str(img_dir),
        "output_path": str(out_dir),
        "classes": ["pessoa", "carro"],
    }


def _start(client: TestClient, img_dir: Path, out_dir: Path, **overrides) -> dict:
    """Helper: POST /start with sensible defaults and return parsed response."""
    body = {
        "mode": "detection",
        "data_path": str(img_dir),
        "output_path": str(out_dir),
        "classes": ["objeto"],
        **overrides,
    }
    return client.post("/api/session/start", json=body)


# ═══════════════════════════════════════════════════════════════════════════════
# A) SCHEMA UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSchemaClasses:
    """Classes field validation in SessionStartRequest."""

    def test_empty_list_is_rejected(self):
        from app.api.schemas import SessionStartRequest

        with pytest.raises(Exception, match="(?i)classe"):
            SessionStartRequest(mode="detection", classes=[], data_path="/tmp")

    def test_whitespace_only_list_is_rejected(self):
        from app.api.schemas import SessionStartRequest

        with pytest.raises(Exception, match="(?i)classe"):
            SessionStartRequest(mode="detection", classes=["   ", "\t", ""], data_path="/tmp")

    def test_classes_are_stripped(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(mode="detection", classes=[" dog ", " cat "], data_path="/tmp")
        assert req.classes == ["dog", "cat"]

    def test_duplicate_classes_are_deduplicated(self):
        """BUG FIX: duplicates created ambiguous category IDs in YOLO export."""
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["dog", "cat", "dog", "cat"], data_path="/tmp"
        )
        assert req.classes == ["dog", "cat"]

    def test_all_same_deduplicated_to_one(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["dog", "dog", "dog"], data_path="/tmp"
        )
        assert req.classes == ["dog"]

    def test_deduplication_preserves_first_occurrence_order(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["cat", "dog", "cat", "bird", "dog"], data_path="/tmp"
        )
        assert req.classes == ["cat", "dog", "bird"]

    def test_unicode_class_names_accepted(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["pessoa", "veículo", "açaí"], data_path="/tmp"
        )
        assert len(req.classes) == 3

    def test_class_name_with_hyphens_and_underscores(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["class-1", "obj_2", "item.3"], data_path="/tmp"
        )
        assert len(req.classes) == 3

    def test_very_long_class_name_accepted(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["a" * 255], data_path="/tmp"
        )
        assert len(req.classes) == 1


class TestSchemaClassificationMode:
    """Classification mode requires >= 2 distinct classes."""

    def test_one_class_is_rejected(self):
        from app.api.schemas import SessionStartRequest

        with pytest.raises(Exception, match="(?i)2 classes"):
            SessionStartRequest(mode="classification", classes=["ok"], data_path="/tmp")

    def test_two_classes_ok(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(mode="classification", classes=["ok", "falha"], data_path="/tmp")
        assert len(req.classes) == 2

    def test_two_duplicate_classes_collapse_to_one_and_fail(self):
        """['ok','ok'] → dedup → ['ok'] → fails classification >= 2 check."""
        from app.api.schemas import SessionStartRequest

        with pytest.raises(Exception):
            SessionStartRequest(mode="classification", classes=["ok", "ok"], data_path="/tmp")

    def test_three_classes_ok(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="classification", classes=["ok", "falha", "incerto"], data_path="/tmp"
        )
        assert len(req.classes) == 3

    def test_other_modes_allow_single_class(self):
        from app.api.schemas import SessionStartRequest, TaskMode

        for mode in [TaskMode.DETECTION, TaskMode.TRACKING, TaskMode.OBB]:
            req = SessionStartRequest(mode=mode, classes=["thing"], data_path="/tmp")
            assert req.classes == ["thing"]


class TestSchemaLegacyNormalization:
    """Frontend sends camelCase / legacy names — schema must normalize them."""

    def test_data_root_maps_to_data_path(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(mode="detection", classes=["c"], data_root="/my/data")
        assert req.data_path == "/my/data"

    def test_data_path_takes_precedence_over_data_root(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["c"], data_path="/primary", data_root="/secondary"
        )
        assert req.data_path == "/primary"

    def test_output_dir_maps_to_output_path(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["c"], data_path="/d", output_dir="/my/out"
        )
        assert req.output_path == "/my/out"

    def test_first_weights_path_maps_to_model_path(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection",
            classes=["c"],
            data_path="/d",
            weights_paths=["/model.pt", "/other.pt"],
        )
        assert req.model_path == "/model.pt"

    def test_resume_existing_maps_to_resume(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["c"], data_path="/d", resume_existing=True
        )
        assert req.resume is True

    def test_resume_or_resume_existing(self):
        """Either flag enables resume."""
        from app.api.schemas import SessionStartRequest

        req_a = SessionStartRequest(
            mode="detection", classes=["c"], data_path="/d", resume=True
        )
        req_b = SessionStartRequest(
            mode="detection", classes=["c"], data_path="/d", resume_existing=True
        )
        assert req_a.resume is True
        assert req_b.resume is True


class TestSchemaBbox:
    """AnnotationUpsert.bbox must have exactly 4 elements."""

    def test_empty_list_rejected(self):
        from app.api.schemas import AnnotationUpsert

        with pytest.raises(Exception, match="4 elementos"):
            AnnotationUpsert(category_id=0, bbox=[])

    def test_three_elements_rejected(self):
        from app.api.schemas import AnnotationUpsert

        with pytest.raises(Exception, match="4 elementos"):
            AnnotationUpsert(category_id=0, bbox=[1, 2, 3])

    def test_five_elements_rejected(self):
        from app.api.schemas import AnnotationUpsert

        with pytest.raises(Exception, match="4 elementos"):
            AnnotationUpsert(category_id=0, bbox=[1, 2, 3, 4, 5])

    def test_four_elements_ok(self):
        from app.api.schemas import AnnotationUpsert

        ann = AnnotationUpsert(category_id=0, bbox=[10.0, 20.0, 50.0, 80.0])
        assert ann.bbox == [10.0, 20.0, 50.0, 80.0]


class TestSchemaCategoryId:
    """category_id must be >= 0 (YOLO class index)."""

    def test_negative_rejected(self):
        from app.api.schemas import AnnotationUpsert

        with pytest.raises(Exception, match=">= 0"):
            AnnotationUpsert(category_id=-1, bbox=[1, 2, 3, 4])

    def test_minus_one_rejected(self):
        from app.api.schemas import AnnotationUpsert

        with pytest.raises(Exception):
            AnnotationUpsert(category_id=-100, bbox=[1, 2, 3, 4])

    def test_zero_ok(self):
        from app.api.schemas import AnnotationUpsert

        assert AnnotationUpsert(category_id=0, bbox=[1, 2, 3, 4]).category_id == 0

    def test_large_positive_ok(self):
        from app.api.schemas import AnnotationUpsert

        assert AnnotationUpsert(category_id=999, bbox=[1, 2, 3, 4]).category_id == 999


class TestSchemaConfidenceThreshold:
    """confidence_threshold must be in [0.0, 1.0]."""

    def test_above_one_rejected(self):
        from app.api.schemas import SessionStartRequest

        with pytest.raises(Exception, match="0.0 e 1.0"):
            SessionStartRequest(
                mode="detection", classes=["c"], data_path="/d", confidence_threshold=1.01
            )

    def test_negative_rejected(self):
        from app.api.schemas import SessionStartRequest

        with pytest.raises(Exception, match="0.0 e 1.0"):
            SessionStartRequest(
                mode="detection", classes=["c"], data_path="/d", confidence_threshold=-0.01
            )

    def test_zero_ok(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["c"], data_path="/d", confidence_threshold=0.0
        )
        assert req.confidence_threshold == 0.0

    def test_one_ok(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["c"], data_path="/d", confidence_threshold=1.0
        )
        assert req.confidence_threshold == 1.0

    def test_typical_value_ok(self):
        from app.api.schemas import SessionStartRequest

        req = SessionStartRequest(
            mode="detection", classes=["c"], data_path="/d", confidence_threshold=0.4
        )
        assert req.confidence_threshold == pytest.approx(0.4)


# ═══════════════════════════════════════════════════════════════════════════════
# B) INTEGRATION — HAPPY PATH
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionStartHappyPath:
    def test_detection_returns_200(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, mode="detection", classes=["dog"])
        assert r.status_code == 200

    def test_tracking_returns_200(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, mode="tracking", classes=["car"])
        assert r.status_code == 200

    def test_obb_returns_200(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, mode="obb", classes=["ship"])
        assert r.status_code == 200

    def test_classification_returns_200(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, mode="classification", classes=["ok", "falha"])
        assert r.status_code == 200

    def test_response_has_session_id(self, client, start_body):
        data = client.post("/api/session/start", json=start_body).json()
        assert isinstance(data.get("session_id"), str) and data["session_id"]

    def test_response_total_frames_counts_images_only(self, client, start_body):
        # img_dir has 2 image files; txt/json are not counted
        assert client.post("/api/session/start", json=start_body).json()["total_frames"] == 2

    def test_response_contains_classes(self, client, start_body):
        data = client.post("/api/session/start", json=start_body).json()
        assert data["classes"] == ["pessoa", "carro"]

    def test_response_contains_mode(self, client, start_body):
        data = client.post("/api/session/start", json=start_body).json()
        assert data["mode"] == "detection"

    def test_response_current_frame_starts_at_zero(self, client, start_body):
        assert client.post("/api/session/start", json=start_body).json()["current_frame"] == 0

    def test_output_directory_is_created(self, client, img_dir, out_dir):
        assert not out_dir.exists()
        _start(client, img_dir, out_dir)
        assert out_dir.is_dir()

    def test_deep_nested_output_dir_is_created(self, client, img_dir, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "output"
        assert not deep.exists()
        _start(client, img_dir, deep)
        assert deep.is_dir()

    def test_nested_images_are_counted(self, client, tmp_path, out_dir):
        data = tmp_path / "deep_data"
        data.mkdir()
        sub = data / "sub"
        sub.mkdir()
        (data / "root.jpg").write_bytes(b"fake")
        (sub / "nested.png").write_bytes(b"fake")
        (data / "ignored.txt").write_text("not an image")
        r = _start(client, data, out_dir)
        assert r.json()["total_frames"] == 2

    def test_empty_dataset_creates_session_with_zero_frames(self, client, tmp_path, out_dir):
        empty = tmp_path / "empty_dataset"
        empty.mkdir()
        r = _start(client, empty, out_dir)
        assert r.status_code == 200
        assert r.json()["total_frames"] == 0

    def test_start_without_model_path(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, model_path=None)
        assert r.status_code == 200

    def test_start_with_valid_model_path(self, client, img_dir, out_dir, tmp_path):
        model = tmp_path / "model.pt"
        model.write_bytes(b"fake_weights" * 100)
        r = _start(client, img_dir, out_dir, model_path=str(model))
        assert r.status_code == 200

    def test_duplicate_classes_deduplicated_in_response(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, classes=["dog", "cat", "dog"])
        assert r.status_code == 200
        classes = r.json()["classes"]
        assert classes == ["dog", "cat"]


# ═══════════════════════════════════════════════════════════════════════════════
# C) INTEGRATION — ERROR PATH (each 422 case documented)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionStartValidationErrors:
    def test_null_data_path_returns_422(self, client, out_dir):
        r = client.post(
            "/api/session/start",
            json={"mode": "detection", "data_path": None, "output_path": str(out_dir), "classes": ["x"]},
        )
        assert r.status_code == 422

    def test_nonexistent_data_path_returns_422(self, client, tmp_path, out_dir):
        r = _start(client, tmp_path / "does_not_exist_xyz", out_dir)
        assert r.status_code == 422
        detail = r.json()["detail"].lower()
        assert "dataset" in detail or "encontrado" in detail

    def test_nonexistent_model_returns_422(self, client, img_dir, out_dir, tmp_path):
        r = _start(client, img_dir, out_dir, model_path=str(tmp_path / "missing.pt"))
        assert r.status_code == 422
        assert "modelo" in r.json()["detail"].lower() or "encontrado" in r.json()["detail"].lower()

    def test_wrong_model_extension_returns_422(self, client, img_dir, out_dir, tmp_path):
        bad = tmp_path / "model.onnx"
        bad.write_bytes(b"fake")
        r = _start(client, img_dir, out_dir, model_path=str(bad))
        assert r.status_code == 422
        assert ".pt" in r.json()["detail"]

    def test_empty_classes_returns_422(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, classes=[])
        assert r.status_code == 422

    def test_whitespace_classes_returns_422(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, classes=["  ", ""])
        assert r.status_code == 422

    def test_classification_single_class_returns_422(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, mode="classification", classes=["ok"])
        assert r.status_code == 422

    def test_invalid_mode_returns_422(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, mode="telepatia")
        assert r.status_code == 422

    def test_confidence_above_one_returns_422(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, confidence_threshold=1.5)
        assert r.status_code == 422

    def test_confidence_negative_returns_422(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, confidence_threshold=-0.1)
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# D) REGRESSION TESTS  — one test per root cause, named explicitly
# ═══════════════════════════════════════════════════════════════════════════════


class TestRegressions:
    def test_REGRESSION_invalid_start_does_not_kill_existing_session(
        self, client, img_dir, out_dir, tmp_path
    ):
        """
        Root cause: session was destroyed before input validation, so an invalid
        second start would kill the first session without replacing it.
        Fix: validation happens before remove_session() is called.
        """
        first = _start(client, img_dir, out_dir)
        assert first.status_code == 200
        first_id = first.json()["session_id"]

        bad = _start(client, img_dir, tmp_path / "bad_out", data_path=str(tmp_path / "nonexistent"))
        assert bad.status_code == 422  # must be rejected

        still_alive = client.get(f"/api/session/{first_id}/status")
        assert still_alive.status_code == 200, (
            "REGRESSION: first session must survive a failed start attempt"
        )
        assert still_alive.json()["status"] == "running"

    def test_REGRESSION_second_valid_start_replaces_first(self, client, img_dir, tmp_path):
        """Auto-stop: a valid second start must cleanly replace the first."""
        out1, out2 = tmp_path / "out1", tmp_path / "out2"
        first_id = _start(client, img_dir, out1).json()["session_id"]
        second = _start(client, img_dir, out2)
        assert second.status_code == 200
        assert second.json()["session_id"] != first_id
        assert client.get(f"/api/session/{first_id}/status").status_code == 404

    def test_REGRESSION_start_clears_previous_annotations(
        self, client, img_dir, tmp_path
    ):
        """
        Root cause: annotation_store not cleared between sessions when the second
        start killed the first but annotations from the first leaked into the new session.
        """
        from app.api import state as _state

        _start(client, img_dir, tmp_path / "out1")
        _state.annotation_store[0] = ["leaked_annotation"]  # simulate leftover

        _start(client, img_dir, tmp_path / "out2")
        assert len(_state.annotation_store) == 0, "Annotations must be wiped on new session start"

    def test_REGRESSION_legacy_stop_clears_annotations(self, client, img_dir, out_dir):
        """
        Root cause: POST /session/stop (legacy) did not call reset_annotations(),
        so annotations from a stopped session could pollute the next one.
        """
        from app.api import state as _state

        _start(client, img_dir, out_dir)
        _state.annotation_store[0] = ["leaked"]

        r = client.post("/api/session/stop")
        assert r.status_code == 200
        assert len(_state.annotation_store) == 0, "Legacy stop must clear annotation_store"

    def test_REGRESSION_explicit_stop_clears_annotations(self, client, img_dir, out_dir):
        """POST /session/{id}/stop must also clear annotations."""
        from app.api import state as _state

        sid = _start(client, img_dir, out_dir).json()["session_id"]
        _state.annotation_store[0] = ["leaked"]

        client.post(f"/api/session/{sid}/stop")
        assert len(_state.annotation_store) == 0

    def test_REGRESSION_duplicate_classes_not_accepted(self, client, img_dir, out_dir):
        """
        Root cause: duplicate class names created ambiguous category_id mapping in
        YOLO export (class 'dog' at index 0 and 2 simultaneously).
        """
        r = _start(client, img_dir, out_dir, classes=["dog", "cat", "dog"])
        assert r.status_code == 200
        returned = r.json()["classes"]
        assert len(returned) == len(set(returned)), "Response must not contain duplicate classes"
        assert returned == ["dog", "cat"]


# ═══════════════════════════════════════════════════════════════════════════════
# E) SESSION STATE & LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════


class TestLegacyStatusEndpoint:
    def test_no_session_returns_inactive_with_null_fields(self, client):
        data = client.get("/api/session/status").json()
        assert data["active"] is False
        assert data["session_id"] is None
        assert data["total_frames"] == 0
        assert data["classes"] == []
        assert data["data_path"] is None
        assert data["output_path"] is None

    def test_active_session_returns_active_true(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        assert client.get("/api/session/status").json()["active"] is True

    def test_active_session_includes_session_id(self, client, img_dir, out_dir):
        expected_id = _start(client, img_dir, out_dir).json()["session_id"]
        assert client.get("/api/session/status").json()["session_id"] == expected_id

    def test_active_session_includes_data_path(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        reported = client.get("/api/session/status").json()["data_path"]
        assert Path(reported).resolve() == img_dir.resolve()

    def test_active_session_includes_output_path(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        reported = client.get("/api/session/status").json()["output_path"]
        assert Path(reported).resolve() == out_dir.resolve()

    def test_active_session_includes_mode(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir, mode="tracking", classes=["car"])
        assert client.get("/api/session/status").json()["mode"] == "tracking"

    def test_active_session_includes_classes(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir, classes=["alpha", "beta"])
        assert client.get("/api/session/status").json()["classes"] == ["alpha", "beta"]

    def test_status_goes_inactive_after_legacy_stop(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        client.post("/api/session/stop")
        assert client.get("/api/session/status").json()["active"] is False


class TestSessionLifecycle:
    def test_stopped_session_returns_404(self, client, img_dir, out_dir):
        sid = _start(client, img_dir, out_dir).json()["session_id"]
        client.post(f"/api/session/{sid}/stop")
        assert client.get(f"/api/session/{sid}/status").status_code == 404

    def test_stop_on_unknown_session_returns_404(self, client):
        assert client.post("/api/session/nonexistent-uuid/stop").status_code == 404

    def test_legacy_stop_when_no_session_is_ok(self, client):
        r = client.post("/api/session/stop")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_stop_returns_output_path(self, client, img_dir, out_dir):
        sid = _start(client, img_dir, out_dir).json()["session_id"]
        r = client.post(f"/api/session/{sid}/stop")
        assert r.status_code == 200
        assert Path(r.json()["output_path"]).resolve() == out_dir.resolve()

    def test_action_on_unknown_session_returns_404(self, client):
        r = client.post("/api/session/nonexistent/action", json={"action": "next"})
        assert r.status_code == 404

    def test_unknown_action_returns_422(self, client, img_dir, out_dir):
        sid = _start(client, img_dir, out_dir).json()["session_id"]
        r = client.post(f"/api/session/{sid}/action", json={"action": "teleport"})
        assert r.status_code == 422

    def test_next_action_advances_frame(self, client, img_dir, out_dir):
        sid = _start(client, img_dir, out_dir).json()["session_id"]
        r = client.post(f"/api/session/{sid}/action", json={"action": "next"})
        assert r.json()["current_frame"] == 1

    def test_prev_on_first_frame_stays_at_zero(self, client, img_dir, out_dir):
        sid = _start(client, img_dir, out_dir).json()["session_id"]
        r = client.post(f"/api/session/{sid}/action", json={"action": "prev"})
        assert r.json()["current_frame"] == 0

    def test_next_at_last_frame_stays_at_last(self, client, img_dir, out_dir):
        """img_dir has 2 images (indices 0 and 1); next twice must clamp at 1."""
        sid = _start(client, img_dir, out_dir).json()["session_id"]
        client.post(f"/api/session/{sid}/action", json={"action": "next"})
        r = client.post(f"/api/session/{sid}/action", json={"action": "next"})
        assert r.json()["current_frame"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# F) METADATA FILE (.inolabel.json)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMetadataFile:
    def test_file_is_written_on_start(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        assert (out_dir / ".inolabel.json").exists()

    def test_file_contains_mode(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir, mode="obb", classes=["ship"])
        meta = json.loads((out_dir / ".inolabel.json").read_text())
        assert meta["mode"] == "obb"

    def test_file_contains_data_path(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        meta = json.loads((out_dir / ".inolabel.json").read_text())
        assert Path(meta["data_path"]).resolve() == img_dir.resolve()

    def test_file_contains_classes(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir, classes=["pessoa", "carro"])
        meta = json.loads((out_dir / ".inolabel.json").read_text())
        assert meta["classes"] == ["pessoa", "carro"]

    def test_file_contains_session_id(self, client, img_dir, out_dir):
        sid = _start(client, img_dir, out_dir).json()["session_id"]
        meta = json.loads((out_dir / ".inolabel.json").read_text())
        assert meta["session_id"] == sid

    def test_file_created_at_is_parseable_iso8601(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        meta = json.loads((out_dir / ".inolabel.json").read_text())
        dt = datetime.fromisoformat(meta["created_at"])
        assert dt.year >= 2024

    def test_file_is_valid_json(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        raw = (out_dir / ".inolabel.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_classes_in_file_are_deduplicated(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir, classes=["dog", "cat", "dog"])
        meta = json.loads((out_dir / ".inolabel.json").read_text())
        assert meta["classes"] == ["dog", "cat"]


# ═══════════════════════════════════════════════════════════════════════════════
# G) PROJECTS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════


class TestProjectsEndpoint:
    def test_missing_root_returns_empty_list(self, client, tmp_path):
        r = client.get(f"/api/session/projects?path={tmp_path / 'nonexistent'}")
        assert r.status_code == 200
        assert r.json() == []

    def test_empty_directory_returns_empty_list(self, client, tmp_path):
        empty = tmp_path / "scan_root"
        empty.mkdir()
        r = client.get(f"/api/session/projects?path={empty}")
        assert r.status_code == 200
        assert r.json() == []

    def test_finds_project_by_metadata_file(self, client, img_dir, tmp_path):
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        out = scan_root / "myproject"
        _start(client, img_dir, out)
        projects = client.get(f"/api/session/projects?path={scan_root}").json()
        assert len(projects) == 1
        assert projects[0]["name"] == "myproject"

    def test_project_has_correct_mode(self, client, img_dir, tmp_path):
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        _start(client, img_dir, scan_root / "p", mode="obb", classes=["ship"])
        projects = client.get(f"/api/session/projects?path={scan_root}").json()
        assert projects[0]["mode"] == "obb"

    def test_project_has_correct_classes(self, client, img_dir, tmp_path):
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        _start(client, img_dir, scan_root / "p", classes=["alpha", "beta"])
        projects = client.get(f"/api/session/projects?path={scan_root}").json()
        assert set(projects[0]["classes"]) == {"alpha", "beta"}

    def test_annotated_frames_counts_nonempty_txt_only(self, client, img_dir, tmp_path):
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        out = scan_root / "p"
        _start(client, img_dir, out)
        labels = out / "labels"
        labels.mkdir(parents=True, exist_ok=True)
        (labels / "img_a.txt").write_text("0 0.5 0.5 0.1 0.1\n")  # non-empty → counted
        (labels / "img_b.txt").write_text("")  # empty → NOT counted
        projects = client.get(f"/api/session/projects?path={scan_root}").json()
        assert projects[0]["annotated_frames"] == 1

    def test_finds_multiple_projects(self, client, img_dir, tmp_path):
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        for name in ["proj_alpha", "proj_beta"]:
            _start(client, img_dir, scan_root / name)
        projects = client.get(f"/api/session/projects?path={scan_root}").json()
        names = {p["name"] for p in projects}
        assert "proj_alpha" in names and "proj_beta" in names

    def test_directory_without_metadata_or_labels_is_ignored(self, client, tmp_path):
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        (scan_root / "random_dir").mkdir()
        projects = client.get(f"/api/session/projects?path={scan_root}").json()
        assert projects == []

    def test_legacy_dir_with_labels_is_discovered(self, client, tmp_path):
        """Directories with a labels/ subdir (but no .inolabel.json) are also listed."""
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        legacy = scan_root / "old_project"
        (legacy / "labels").mkdir(parents=True)
        (legacy / "labels" / "img.txt").write_text("0 0.5 0.5 0.1 0.1\n")
        projects = client.get(f"/api/session/projects?path={scan_root}").json()
        assert len(projects) == 1
        assert projects[0]["mode"] == "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# H) EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_path_with_spaces_ok(self, client, tmp_path, out_dir):
        spaced = tmp_path / "my dataset folder"
        spaced.mkdir()
        (spaced / "img.jpg").write_bytes(b"fake")
        r = _start(client, spaced, out_dir)
        assert r.status_code == 200

    def test_class_names_with_slashes_and_dashes(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, classes=["pessoa-adulta", "veículo/caminhão"])
        assert r.status_code == 200

    def test_class_with_unicode_accents(self, client, img_dir, out_dir):
        r = _start(client, img_dir, out_dir, classes=["veículo", "ônibus", "açaí"])
        assert r.status_code == 200
        assert len(r.json()["classes"]) == 3

    def test_single_image_file_as_data_path(self, client, tmp_path, out_dir):
        single = tmp_path / "img.jpg"
        single.write_bytes(b"\xff\xd8\xff")
        r = _start(client, single, out_dir)
        assert r.status_code == 200
        assert r.json()["total_frames"] == 1

    def test_validate_then_start_flow(self, client, img_dir, out_dir):
        """Typical frontend flow: validate-path first, then start."""
        v = client.post("/api/session/validate-path", json={"path": str(img_dir)})
        assert v.json()["valid"] is True
        r = _start(client, img_dir, out_dir)
        assert r.status_code == 200

    def test_status_endpoint_always_returns_200(self, client):
        """GET /session/status must never 4xx, even without a session."""
        assert client.get("/api/session/status").status_code == 200

    def test_annotation_add_out_of_bounds_returns_400(self, client, img_dir, out_dir):
        """image_id beyond total_frames must be rejected, not silently stored."""
        _start(client, img_dir, out_dir)  # 2 frames → valid ids: 0, 1
        r = client.post(
            "/api/annotations/99",
            json={"category_id": 0, "bbox": [10, 10, 50, 50]},
        )
        assert r.status_code == 400

    def test_annotation_negative_category_id_returns_422(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        r = client.post(
            "/api/annotations/0",
            json={"category_id": -1, "bbox": [10, 10, 50, 50]},
        )
        assert r.status_code == 422

    def test_annotation_wrong_bbox_length_returns_422(self, client, img_dir, out_dir):
        _start(client, img_dir, out_dir)
        r = client.post(
            "/api/annotations/0",
            json={"category_id": 0, "bbox": [10, 10, 50]},
        )
        assert r.status_code == 422
