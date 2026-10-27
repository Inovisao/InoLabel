"""Proposal generation, durable review, and recovery without real model downloads."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.api import state
from app.api.annotations import service as annotations
from app.api.annotations.schemas import AnnotationPatch, AnnotationUpsert
from app.api.common.errors import InvalidInput, NotFound
from app.api.frames.service import init_frames
from app.autolabeling import jobs, service
from app.autolabeling.models import ModelConfig, ReviewRequest, RunRequest
from app.autolabeling.storage import read_run, run_path
from app.core.project_state.paths import state_path


class InlineExecutor:
    def submit(self, function, *args):
        function(*args)


class FakeAdapter:
    def __init__(self, path):
        pass

    def inspect(self):
        return {0: 'person'}

    def predict(self, image, config, classes):
        return [(classes.index(config.class_mapping['person']), [2., 3., 10., 12.], 0.9)]


@pytest.fixture
def project(tmp_path, monkeypatch):
    state.coco_writer.flush()
    state.reset_state()
    images = tmp_path / 'images'
    images.mkdir()
    for name in ['a.png', 'b.png']:
        cv2.imwrite(str(images / name), np.zeros((40, 50, 3), np.uint8))
    weights = tmp_path / 'model.pt'
    weights.write_bytes(b'test checkpoint')
    output = tmp_path / 'project'
    output.mkdir()
    session = state.create_session(mode='detection', data_path=images, output_path=output, classes=['person'])
    init_frames()
    monkeypatch.setattr(jobs, 'create_adapter', lambda adapter_id, path: FakeAdapter(path))
    monkeypatch.setattr(jobs, 'executor', InlineExecutor())
    config = ModelConfig(model_path=str(weights), class_mapping={'person': 'person'})
    yield session, config
    state.coco_writer.flush()
    state.reset_state()


def generate(project, indices=None):
    session, config = project
    result = service.create_run(RunRequest(session_id=session.session_id, config=config, frame_indices=indices))
    return service.proposals(result['id'])


def test_generation_does_not_mutate_annotations(project):
    result = generate(project)
    assert result['run']['status'] == 'succeeded'
    assert result['run']['processed'] == 2
    assert len(result['proposals']) == 2
    assert state.annotation_store == {}
    assert not state.reviewed_frames


def test_accept_preserves_manual_and_is_idempotent(project):
    annotations.add_annotation(0, AnnotationUpsert(category_id=0, bbox=[1, 1, 5, 5]))
    run = generate(project, [0])
    request = ReviewRequest(proposal_id=run['proposals'][0]['id'])
    first = service.review(run['run']['id'], request, 'accept')
    repeated = service.review(run['run']['id'], request, 'accept')
    assert first['annotation']['id'] == repeated['annotation']['id']
    assert len(state.annotation_store[0]) == 2
    data = json.loads(state_path(project[0].output_path, 'detection').read_text())
    assert len(data['annotations']) == 2
    assert (project[0].output_path / 'labels' / 'a.txt').is_file()


def test_accept_survives_manifest_write_failure(project, monkeypatch):
    run = generate(project, [0])
    request = ReviewRequest(proposal_id=run['proposals'][0]['id'])
    original = service.write_run
    def fail(*args):
        raise OSError('disk unavailable')
    monkeypatch.setattr(service, 'write_run', fail)
    with pytest.raises(OSError):
        service.review(run['run']['id'], request, 'accept')
    assert len(state.annotation_store[0]) == 1
    monkeypatch.setattr(service, 'write_run', original)
    service.review(run['run']['id'], request, 'accept')
    assert len(state.annotation_store[0]) == 1


def test_accept_recovers_after_restart(project, monkeypatch):
    run = generate(project, [0])
    request = ReviewRequest(proposal_id=run['proposals'][0]['id'])
    original = service.write_run
    monkeypatch.setattr(service, 'write_run', lambda *args: (_ for _ in ()).throw(OSError()))
    with pytest.raises(OSError):
        service.review(run['run']['id'], request, 'accept')
    monkeypatch.setattr(service, 'write_run', original)
    init_frames()
    service.review(run['run']['id'], request, 'accept')
    assert len(state.annotation_store[0]) == 1


def test_edit_before_accept_and_undo(project):
    run = generate(project, [0])
    request = ReviewRequest(proposal_id=run['proposals'][0]['id'], bbox=[4, 5, 6, 7])
    result = service.review(run['run']['id'], request, 'accept')
    assert result['annotation']['bbox'] == [4, 5, 6, 7]
    service.review(run['run']['id'], request, 'undo')
    assert not state.annotation_store[0]
    assert service.proposals(run['run']['id'])['proposals'][0]['status'] == 'pending'
    service.review(run['run']['id'], request, 'accept')
    assert len(state.annotation_store[0]) == 1


def test_undo_does_not_remove_human_correction(project):
    run = generate(project, [0])
    request = ReviewRequest(proposal_id=run['proposals'][0]['id'])
    result = service.review(run['run']['id'], request, 'accept')
    annotations.update_annotation(0, result['annotation']['id'], AnnotationPatch(bbox=[5, 5, 8, 8]))
    with pytest.raises(InvalidInput, match='edited'):
        service.review(run['run']['id'], request, 'undo')
    assert state.annotation_store[0][0].bbox == [5, 5, 8, 8]


def test_reject_does_not_create_labels(project):
    run = generate(project, [0])
    request = ReviewRequest(proposal_id=run['proposals'][0]['id'])
    service.review(run['run']['id'], request, 'reject')
    assert state.annotation_store == {}
    with pytest.raises(InvalidInput, match='Rejected'):
        service.review(run['run']['id'], request, 'accept')


def test_changed_taxonomy_is_rejected(project):
    run = generate(project, [0])
    state.active_session().classes = ['car']
    with pytest.raises(InvalidInput, match='classes'):
        service.review(run['run']['id'], ReviewRequest(proposal_id=run['proposals'][0]['id']), 'accept')


def test_changed_image_is_rejected(project):
    run = generate(project, [0])
    state.frame_paths[0].write_bytes(b'changed')
    with pytest.raises(InvalidInput, match='image changed'):
        service.review(run['run']['id'], ReviewRequest(proposal_id=run['proposals'][0]['id']), 'accept')


def test_another_active_project_cannot_accept_old_run(project, tmp_path):
    run = generate(project, [0])
    state.create_session(mode='detection', data_path=project[0].data_path, output_path=tmp_path/'other', classes=['person'])
    with pytest.raises(NotFound):
        service.review(run['run']['id'], ReviewRequest(proposal_id=run['proposals'][0]['id']), 'accept')


@pytest.mark.parametrize('indices', [[-1], [2], [0, 0], []])
def test_bad_frame_selection(project, indices):
    with pytest.raises(InvalidInput):
        generate(project, indices)


def test_unmapped_model_rejected(project):
    project[1].class_mapping = {}
    with pytest.raises(InvalidInput, match='Map at least'):
        generate(project, [0])


def test_directory_cannot_be_used_as_checkpoint(project, tmp_path):
    from app.autolabeling.adapters.ultralytics import checkpoint
    directory = tmp_path / 'fake.pt'
    directory.mkdir()
    with pytest.raises(InvalidInput):
        checkpoint(directory)


def test_no_numeric_class_fallback():
    from app.api.inference.detections import _category_id
    assert _category_id('person', 0, ['car']) is None
    assert _category_id('PERSON', 8, ['person']) == 0


def test_corrupt_image_is_failure_not_negative(project):
    state.frame_paths[0].write_bytes(b'broken image')
    result = generate(project)
    assert result['run']['failed'] == 1
    assert result['run']['status'] == 'partially_failed'
    assert not state.reviewed_frames
    assert len(result['proposals']) == 1


def test_model_error_is_visible(project, monkeypatch):
    class Broken(FakeAdapter):
        def inspect(self):
            raise RuntimeError('model failed')
    monkeypatch.setattr(jobs, 'create_adapter', lambda adapter_id, path: Broken(path))
    result = generate(project, [0])
    assert result['run']['status'] == 'failed'
    assert 'model failed' in result['run']['error']


def test_cancel_and_resume_preserves_completed_proposals(project, monkeypatch):
    session, config = project
    original = jobs.executor
    tasks = []
    class Deferred:
        def submit(self, function, *args):
            tasks.append((function, args))
    monkeypatch.setattr(jobs, 'executor', Deferred())
    result = service.create_run(RunRequest(session_id=session.session_id, config=config))
    service.stop_run(result['id'])
    function, args = tasks.pop()
    function(*args)
    assert service.proposals(result['id'])['run']['status'] == 'cancelled'
    monkeypatch.setattr(jobs, 'executor', original)
    service.resume_run(result['id'])
    done = service.proposals(result['id'])
    assert done['run']['status'] == 'succeeded'
    assert len(done['proposals']) == 2


def test_interrupted_run_detected(project):
    result = generate(project, [0])
    path = run_path(project[0].output_path, result['run']['id'])
    run = json.loads(path.read_text())
    run['status'] = 'running'
    path.write_text(json.dumps(run))
    assert service.runs()[0]['status'] == 'interrupted'


def test_path_traversal_rejected(project):
    with pytest.raises(NotFound):
        service.proposals('../../escape')


def test_review_validates_finite_coordinates():
    with pytest.raises(ValueError):
        ReviewRequest(proposal_id='p', bbox=[0, 0, float('nan'), 3])


def test_review_validates_image_bounds(project):
    run = generate(project, [0])
    with pytest.raises(InvalidInput, match='inside'):
        service.review(run['run']['id'], ReviewRequest(proposal_id=run['proposals'][0]['id'], bbox=[40, 0, 30, 5]), 'accept')
    assert not state.annotation_store


def test_http_generation_review_and_configuration(project, monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import app
    monkeypatch.setattr(service, 'create_adapter', lambda adapter_id, path: FakeAdapter(path))
    client = TestClient(app)
    session, config = project
    inspected = client.post('/api/autolabeling/models/inspect', json=config.model_dump())
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()['classes'] == ['person']
    response = client.post('/api/autolabeling/runs', json={
        'session_id': session.session_id, 'config': config.model_dump(), 'frame_indices': [0],
    })
    assert response.status_code == 200, response.text
    run_id = response.json()['id']
    proposals = client.get(f'/api/autolabeling/runs/{run_id}/proposals').json()['proposals']
    accepted = client.post(f'/api/autolabeling/runs/{run_id}/accept', json={'proposal_id': proposals[0]['id']})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['proposal']['status'] == 'accepted'
    assert client.get('/api/autolabeling/config').json()['model_path'] == config.model_path
    assert client.get('/api/autolabeling/runs').json()[0]['accepted'] == 1


def test_http_rejects_stale_session_and_invalid_threshold(project):
    from fastapi.testclient import TestClient
    from app.api.main import app
    client = TestClient(app)
    config = project[1].model_dump()
    response = client.post('/api/autolabeling/runs', json={'session_id': 'stale', 'config': config})
    assert response.status_code == 422
    config['confidence'] = 1.5
    assert client.post('/api/autolabeling/models/inspect', json=config).status_code == 422


def test_adapter_maps_only_explicit_classes(project, monkeypatch):
    from app.autolabeling.adapters import ultralytics
    class Value:
        def __init__(self, value): self.value = value
        def item(self): return self.value
    class Coordinates:
        def __getitem__(self, index): return self
        def detach(self): return self
        def cpu(self): return self
        def tolist(self): return [-2, -3, 60, 45]
    class Box:
        cls = Value(0)
        conf = Value(.9)
        xyxy = Coordinates()
    class Result:
        boxes = [Box()]
    class Detector:
        task = 'detect'
        names = {0: 'person'}
        def __init__(self, path): pass
        def load(self): return self
        def predict(self, *args, **kwargs): return [Result()]
    monkeypatch.setattr(ultralytics, 'Detector', Detector)
    adapter = ultralytics.YoloAdapter(project[1].model_path)
    adapter.inspect()
    config = ModelConfig(model_path=project[1].model_path, class_mapping={'person': 'car'})
    result = adapter.predict(np.zeros((40, 50, 3), np.uint8), config, ['car'])
    assert result[0][:2] == (0, [0., 0., 50., 40.])
    config.class_mapping = {}
    assert adapter.predict(np.zeros((40, 50, 3), np.uint8), config, ['car']) == []


def test_job_finishes_in_original_project_after_session_switch(project, tmp_path, monkeypatch):
    deferred = []
    class Deferred:
        def submit(self, function, *args): deferred.append((function, args))
    monkeypatch.setattr(jobs, 'executor', Deferred())
    session, config = project
    result = service.create_run(RunRequest(session_id=session.session_id, config=config, frame_indices=[0]))
    state.create_session(mode='detection', data_path=session.data_path, output_path=tmp_path/'other', classes=['car'])
    state.annotation_store.clear()
    function, args = deferred.pop()
    function(*args)
    saved = read_run(session.output_path, result['id'])
    assert saved['status'] == 'succeeded'
    assert saved['proposals'][0]['class_name'] == 'person'
    assert not state.annotation_store
    assert not (tmp_path/'other'/'.inolabel').exists()


def test_reading_paginated_proposals(project):
    run = generate(project)
    first = service.proposals(run['run']['id'], offset=0, limit=1)
    second = service.proposals(run['run']['id'], offset=1, limit=1)
    assert first['total'] == second['total'] == 2
    assert first['proposals'][0]['id'] != second['proposals'][0]['id']
    assert len(service.proposals(run['run']['id'], frame_index=1)['proposals']) == 1


def test_zero_predictions_do_not_mark_reviewed(project, monkeypatch):
    monkeypatch.setattr(FakeAdapter, 'predict', lambda *args: [])
    result = generate(project)
    assert result['run']['status'] == 'succeeded'
    assert not result['proposals']
    assert not state.reviewed_frames


def test_model_change_prevents_resuming(project):
    run = generate(project, [0])
    path = run_path(project[0].output_path, run['run']['id'])
    record = json.loads(path.read_text())
    record['status'] = 'interrupted'
    path.write_text(json.dumps(record))
    Path(project[1].model_path).write_bytes(b'new model')
    service.resume_run(run['run']['id'])
    result = service.proposals(run['run']['id'])
    assert result['run']['status'] == 'failed'
    assert 'checkpoint changed' in result['run']['error']
    assert len(result['proposals']) == 1


def test_resume_retries_only_failed_images(project, monkeypatch):
    calls = []
    class Unstable(FakeAdapter):
        def predict(self, image, config, classes):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('temporary failure')
            return super().predict(image, config, classes)
    monkeypatch.setattr(jobs, 'create_adapter', lambda adapter_id, path: Unstable(path))
    run = generate(project)
    assert run['run']['status'] == 'partially_failed'
    service.resume_run(run['run']['id'])
    result = service.proposals(run['run']['id'])
    assert result['run']['status'] == 'succeeded'
    assert len(calls) == 3
    assert len(result['proposals']) == 2


def test_old_disk_receipt_does_not_hide_failed_geometry_save(project, monkeypatch):
    run = generate(project, [0])
    request = ReviewRequest(proposal_id=run['proposals'][0]['id'])
    service.review(run['run']['id'], request, 'accept')
    state.annotation_store[0][0].bbox = [5, 5, 10, 10]
    monkeypatch.setattr(service, 'save_project_state', lambda: None)
    with pytest.raises(InvalidInput, match='confirm'):
        service.review(run['run']['id'], request, 'accept')


def test_missing_ultralytics_explains_the_active_interpreter(monkeypatch):
    import builtins
    import sys
    from app.core.detector import Detector
    from app.core.model_runtime import ModelRuntimeError
    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == 'ultralytics':
            raise ModuleNotFoundError("No module named 'ultralytics'", name='ultralytics')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', missing)
    with pytest.raises(ModelRuntimeError) as error:
        Detector('model.pt').load()
    assert sys.executable in str(error.value)
    assert 'python -m pip install -r requirements.txt' in str(error.value)
    assert 'ultralytics' in str(error.value)


def test_runtime_diagnostics_do_not_import_torch(monkeypatch):
    import builtins
    from app.core.model_runtime import runtime_info
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name not in ('torch', 'torchvision', 'ultralytics')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    result = runtime_info()
    assert result['executable']
    assert 'ultralytics' in result['packages']
    assert result['project_python'] == '3.9'
