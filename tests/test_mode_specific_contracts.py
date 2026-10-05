from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


@pytest.fixture
def image_dir(tmp_path: Path) -> Path:
    import cv2
    import numpy as np

    root = tmp_path / "images"
    root.mkdir()
    cv2.imwrite(str(root / "frame_a.jpg"), np.full((60, 80, 3), (0, 0, 255), dtype=np.uint8))
    cv2.imwrite(str(root / "frame_b.jpg"), np.full((60, 80, 3), (0, 255, 0), dtype=np.uint8))
    return root


def _start(
    client: TestClient,
    image_dir: Path,
    output_dir: Path,
    mode: str,
    classes=None,
    model_path: Path | None = None,
) -> str:
    response = client.post(
        "/api/session/start",
        json={
            "mode": mode,
            "data_path": str(image_dir),
            "output_path": str(output_dir),
            "model_path": str(model_path) if model_path is not None else None,
            "classes": classes or ["person", "car"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def test_detection_annotations_reject_track_id(client: TestClient, image_dir: Path, tmp_path: Path):
    _start(client, image_dir, tmp_path / "out", "detection")

    response = client.post(
        "/api/annotations/0",
        json={
            "category_id": 0,
            "bbox": [1, 2, 30, 40],
            "track_id": 7,
            "source": "model",
        },
    )

    assert response.status_code == 422
    assert "track_id" in response.json()["detail"]


def test_tracking_model_annotations_require_track_id(client: TestClient, image_dir: Path, tmp_path: Path):
    _start(client, image_dir, tmp_path / "out", "tracking")

    response = client.post(
        "/api/annotations/0",
        json={
            "category_id": 0,
            "bbox": [1, 2, 30, 40],
            "source": "model",
        },
    )

    assert response.status_code == 422
    assert "track_id" in response.json()["detail"]


def test_obb_mode_returns_obb_payload_from_bbox(client: TestClient, image_dir: Path, tmp_path: Path):
    _start(client, image_dir, tmp_path / "out", "obb", classes=["ship"])

    response = client.post(
        "/api/annotations/0",
        json={"category_id": 0, "bbox": [10, 20, 30, 40], "source": "manual"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["obb"] == {
        "cx": 25.0,
        "cy": 40.0,
        "width": 30.0,
        "height": 40.0,
        "angle": 0.0,
        "angle_unit": "degrees",
        "points": [[10.0, 20.0], [40.0, 20.0], [40.0, 60.0], [10.0, 60.0]],
    }


def test_classification_mode_rejects_bbox_annotations(client: TestClient, image_dir: Path, tmp_path: Path):
    _start(client, image_dir, tmp_path / "out", "classification", classes=["ok", "fail"])

    response = client.post(
        "/api/annotations/0",
        json={"category_id": 0, "bbox": [1, 2, 30, 40], "source": "manual"},
    )

    assert response.status_code == 422
    assert "Classificacao" in response.json()["detail"] or "Classificação" in response.json()["detail"]


def test_classification_endpoint_copies_image_to_class_folder(
    client: TestClient, image_dir: Path, tmp_path: Path
):
    output_dir = tmp_path / "out"
    _start(client, image_dir, output_dir, "classification", classes=["ok", "fail"])
    client.get("/api/frames/init")

    response = client.post(
        "/api/annotations/0/classification",
        json={"category_id": 1},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["top1_class_id"] == 1
    assert payload["top1_class_name"] == "fail"
    assert Path(payload["destination_path"]).name == "frame_a.jpg"
    assert Path(payload["destination_path"]).parent.name == "fail"
    assert (output_dir / "fail" / "frame_a.jpg").exists()
    assert (output_dir / "classification_state.json").exists()


def test_tracking_coco_export_preserves_track_id(client: TestClient, image_dir: Path, tmp_path: Path):
    session_id = _start(client, image_dir, tmp_path / "out", "tracking")
    client.get("/api/frames/init")
    response = client.post(
        "/api/annotations/0",
        json={
            "category_id": 0,
            "bbox": [10, 10, 20, 20],
            "track_id": 42,
            "source": "model",
        },
    )
    assert response.status_code == 200, response.text

    export = client.post(
        "/api/export",
        json={
            "session_id": session_id,
            "destination": str(tmp_path),
            "name": "tracking_export",
            "formats": ["coco"],
            "use_split": False,
        },
    )

    assert export.status_code == 200, export.text
    annotations = (tmp_path / "tracking_export" / "annotations.json").read_text(encoding="utf-8")
    assert '"track_id": 42' in annotations


def test_obb_yolo_export_writes_oriented_label(client: TestClient, image_dir: Path, tmp_path: Path):
    session_id = _start(client, image_dir, tmp_path / "out", "obb", classes=["ship"])
    client.get("/api/frames/init")
    response = client.post(
        "/api/annotations/0",
        json={"category_id": 0, "bbox": [10, 20, 30, 20], "source": "manual"},
    )
    assert response.status_code == 200, response.text

    export = client.post(
        "/api/export",
        json={
            "session_id": session_id,
            "destination": str(tmp_path),
            "name": "obb_export",
            "formats": ["yolo"],
            "use_split": False,
        },
    )

    assert export.status_code == 200, export.text
    label_path = tmp_path / "obb_export" / "labels" / "train" / "frame_a.txt"
    values = label_path.read_text(encoding="utf-8").strip().split()
    assert len(values) == 9
    assert values[0] == "0"


def test_tracking_inference_endpoint_returns_and_saves_track_ids(
    client: TestClient, image_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"fake model")
    session_id = _start(
        client,
        image_dir,
        tmp_path / "out",
        "tracking",
        classes=["person"],
        model_path=model_path,
    )
    client.get("/api/frames/init")

    from app.api.routes import inference

    class FakeBox:
        conf = 0.9
        cls = 0

        @property
        def xyxy(self):
            import numpy as np

            class _Array:
                def cpu(self):
                    return self

                def numpy(self):
                    return np.array([[10, 12, 30, 42]], dtype=np.float32)

            return _Array()

    class FakeResult:
        names = {0: "person"}
        boxes = [FakeBox()]

    class FakeDetector:
        def __init__(self, model_path):
            self.model_path = model_path

        def predict(self, frame, **kwargs):
            return [FakeResult()]

    class FakeTrack:
        track_id = 77
        score = 0.91

        @property
        def tlbr(self):
            import numpy as np

            return np.array([10, 12, 30, 42], dtype=np.float32)

    class FakeTracker:
        instances = 0

        def __init__(self, args, frame_rate):
            FakeTracker.instances += 1

        def update(self, boxes, scores, category_ids, img_info, img_size):
            return [(0, FakeTrack())]

    monkeypatch.setattr(inference, "Detector", FakeDetector)
    monkeypatch.setattr(inference, "MultiClassByteTracker", FakeTracker)

    response = client.post(
        "/api/inference/tracking",
        json={"session_id": session_id, "frame_indices": [0, 1], "save_annotations": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "tracking"
    assert payload["processed_frames"] == 2
    assert FakeTracker.instances == 1
    assert payload["frames"][0]["frame_index"] == 0
    assert payload["frames"][0]["timestamp"] == 0.0
    detection = payload["frames"][0]["detections"][0]
    assert detection["bbox"] == [10.0, 12.0, 30.0, 42.0]
    assert detection["class_id"] == 0
    assert detection["class_name"] == "person"
    assert detection["track_id"] == 77

    saved = client.get("/api/annotations/0").json()
    assert saved[0]["track_id"] == 77
    assert saved[0]["bbox"] == [10.0, 12.0, 20.0, 30.0]


def test_tracking_inference_endpoint_rejects_detection_session(
    client: TestClient, image_dir: Path, tmp_path: Path
):
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"fake model")
    session_id = _start(
        client,
        image_dir,
        tmp_path / "out",
        "detection",
        classes=["person"],
        model_path=model_path,
    )
    client.get("/api/frames/init")

    response = client.post(
        "/api/inference/tracking",
        json={"session_id": session_id, "frame_indices": [0]},
    )

    assert response.status_code == 422
    assert "tracking" in response.json()["detail"]


def test_tracking_inference_endpoint_processes_video_without_autosave(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import cv2
    import numpy as np

    video_path = tmp_path / "video.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10,
        (32, 24),
    )
    writer.write(np.full((24, 32, 3), 10, dtype=np.uint8))
    writer.write(np.full((24, 32, 3), 20, dtype=np.uint8))
    writer.release()

    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"fake model")
    response = client.post(
        "/api/session/start",
        json={
            "mode": "tracking",
            "data_path": str(video_path),
            "output_path": str(tmp_path / "out"),
            "model_path": str(model_path),
            "classes": ["person"],
        },
    )
    assert response.status_code == 200, response.text
    session_id = response.json()["session_id"]

    from app.api.routes import inference

    class FakeBox:
        conf = 0.9
        cls = 0

        @property
        def xyxy(self):
            import numpy as np

            class _Array:
                def cpu(self):
                    return self

                def numpy(self):
                    return np.array([[1, 2, 10, 12]], dtype=np.float32)

            return _Array()

    class FakeResult:
        names = {0: "person"}
        boxes = [FakeBox()]

    class FakeDetector:
        def __init__(self, model_path):
            self.model_path = model_path

        def predict(self, frame, **kwargs):
            return [FakeResult()]

    class FakeTrack:
        track_id = 5
        score = 0.9

        @property
        def tlbr(self):
            import numpy as np

            return np.array([1, 2, 10, 12], dtype=np.float32)

    class FakeTracker:
        def __init__(self, args, frame_rate):
            pass

        def update(self, boxes, scores, category_ids, img_info, img_size):
            return [(0, FakeTrack())]

    monkeypatch.setattr(inference, "Detector", FakeDetector)
    monkeypatch.setattr(inference, "MultiClassByteTracker", FakeTracker)

    result = client.post(
        "/api/inference/tracking",
        json={
            "session_id": session_id,
            "frame_indices": [0, 1],
            "save_annotations": False,
            "frame_rate": 10,
        },
    )

    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload["processed_frames"] == 2
    assert payload["frames"][1]["timestamp"] == 0.1
    assert payload["frames"][1]["detections"][0]["track_id"] == 5
