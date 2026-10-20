"""Retomar o projeto no frame onde a anotação parou, mesmo sem encerrar a sessão."""

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.state import reset_state


@pytest.fixture()
def client(tmp_path):
    reset_state()
    data = tmp_path / "dataset"
    data.mkdir()
    for i in range(5):
        cv2.imwrite(str(data / f"img_{i}.jpg"), np.zeros((20, 30, 3), np.uint8))
    c = TestClient(app)
    yield c, data, tmp_path / "projeto"
    c.post("/api/session/stop")
    reset_state()


def _open(c, data, out, resume):
    body = {"mode": "detection", "data_path": str(data), "output_path": str(out), "classes": ["a"], "resume_existing": resume}
    r = c.post("/api/session/start", json=body)
    assert r.status_code == 200, r.text
    return c.get("/api/frames/init").json()["current_index"]


def test_reopens_where_annotation_stopped_even_if_app_was_closed(client):
    c, data, out = client
    assert _open(c, data, out, resume=False) == 0
    c.post("/api/frames/next")
    c.post("/api/frames/next")
    c.post("/api/frames/next")

    # Fechar a janela/o app não chama /session/stop: o estado em memória some.
    reset_state()

    assert _open(c, data, out, resume=True) == 3
    assert c.get("/api/frames/current").json()["index"] == 3


def test_going_back_is_also_remembered(client):
    c, data, out = client
    _open(c, data, out, resume=False)
    c.post("/api/frames/goto/4")
    c.post("/api/frames/prev")
    reset_state()
    assert _open(c, data, out, resume=True) == 3


def test_new_session_without_resume_starts_at_first_frame(client):
    c, data, out = client
    _open(c, data, out, resume=False)
    c.post("/api/frames/goto/2")
    reset_state()
    assert _open(c, data, out, resume=False) == 0
