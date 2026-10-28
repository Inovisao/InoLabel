"""Catalog extensibility, configuration validation, and SAM 3 provider boundaries."""

from dataclasses import replace

import numpy as np
import pytest
from pydantic import Field, ValidationError

from app.api.common.errors import InvalidInput
from app.autolabeling.adapters import sam3
from app.autolabeling.model_catalog import registry, settings
from app.autolabeling.model_catalog.configuration import resolve_config
from app.autolabeling.model_catalog.schemas import ModelDefinition, ModelInputs
from app.autolabeling.models import ModelConfig


class DemoAdapter:
    def __init__(self, path): self.path = path


class DemoInputs(ModelInputs):
    instruction: str = Field(min_length=1, title='Instrução')
    limit: int = Field(default=3, ge=1, le=10)

    def project_classes(self): return ['object']


def config(**updates):
    values = {'adapter': 'sam3', 'model_id': 'sam3', 'parameters': {
        'class_prompts': [{'class_name': 'wasp', 'text': 'a wasp'}, {'class_name': 'bee', 'text': 'a bee'}],
    }}
    values.update(updates)
    return ModelConfig(**values)


def test_catalog_does_not_import_model_sdks(monkeypatch):
    import builtins
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name not in ('torch', 'ultralytics', 'inference', 'sam3')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    models = registry.catalog('detect_boxes')
    assert {'ultralytics', 'sam3', 'ollama-qwen3-vl-4b', 'ollama-qwen3-vl-8b', 'ollama-gemma3-4b'} <= {m['id'] for m in models}
    entry = next(m for m in models if m['id'] == 'sam3')
    assert entry['source'] == 'catalog'
    assert entry['input_schema']['properties']['class_prompts']['x-control'] == 'class-prompts'
    assert registry.catalog('classify_image') == []


def test_third_model_registers_without_changing_core():
    definition = ModelDefinition(id='demo', name='Demo', adapter='demo', source='catalog',
        description='Test provider', inputs=DemoInputs, factory=f'{__name__}:DemoAdapter',
        strategy='prompt_based', requires_checkpoint=False, required_packages=())
    try:
        registry.DEFINITIONS['demo'] = definition
        model = ModelConfig(adapter='demo', model_id='demo', parameters={'instruction': 'Find objects'})
        normalized, found = resolve_config(model, ['object'])
        assert found is definition
        assert normalized.parameters['limit'] == 3
        assert isinstance(registry.construct_adapter('demo', ''), DemoAdapter)
        described = next(m for m in registry.catalog() if m['id'] == 'demo')
        assert described['availability'] == 'configured'
        assert described['input_schema']['properties']['instruction']['type'] == 'string'
        with pytest.raises(ValidationError):
            ModelConfig(adapter='demo', parameters={'instruction': 'Find', 'limit': 99})
    finally:
        registry.DEFINITIONS.pop('demo', None)


@pytest.mark.parametrize('parameters', [
    {}, {'class_prompts': []}, {'class_prompts': [{'class_name': 'wasp', 'text': '  '}]},
    {'class_prompts': [{'class_name': 'wasp', 'text': 'wasp'}, {'class_name': 'wasp', 'text': 'insect'}]},
    {'class_prompts': [{'class_name': 'wasp', 'text': 'wasp'}], 'score_threshold': float('nan')},
    {'class_prompts': [{'class_name': 'wasp', 'text': 'wasp'}], 'device': 'arbitrary'},
    {'class_prompts': [{'class_name': 'wasp', 'text': 'wasp'}], 'api_key': 'must-not-be-persisted'},
])
def test_sam_inputs_validate_at_boundary(parameters):
    with pytest.raises(ValidationError): config(parameters=parameters)


def test_model_adapter_identity_must_match():
    with pytest.raises(ValidationError): config(adapter='ultralytics')
    with pytest.raises(ValidationError): ModelConfig(adapter='not-installed', model_path='x.pt')


def test_legacy_yolo_configuration_is_readable():
    cfg = ModelConfig.model_validate({'model_path': '/weights.pt', 'confidence': .5, 'class_mapping': {'car': 'car'}})
    assert cfg.adapter == 'ultralytics'
    assert cfg.parameters == {}


def checkpoint_definition(monkeypatch):
    definition = replace(registry.DEFINITIONS['sam3'], requires_checkpoint=True,
                         runtime_status='', preparation='', required_environment=())
    monkeypatch.setitem(registry.DEFINITIONS, 'sam3', definition)


def test_local_setup_resolves_without_copying_weights(tmp_path, monkeypatch):
    checkpoint_definition(monkeypatch)
    monkeypatch.setattr(settings.app_config, 'LOCAL_DIR', tmp_path/'local')
    path = tmp_path/'sam3.pt'
    path.write_bytes(b'checkpoint')
    settings.save_setup('sam3', settings.ModelSetup(model_path=str(path)))
    resolved, _ = resolve_config(config(), ['bee', 'wasp'])
    assert resolved.model_path == str(path)
    assert path.read_bytes() == b'checkpoint'
    with pytest.raises(InvalidInput): settings.read_setup('../../escape')


def test_unknown_project_class_rejected():
    with pytest.raises(InvalidInput, match='prompts'):
        resolve_config(config(), ['car'])


class Worker:
    def __init__(self): self.calls = []; self.closed = False
    def close(self): self.closed = True
    def predict(self, image, prompts, threshold, iou):
        import cv2
        assert cv2.imread(str(image)).shape == (40, 50, 3)
        self.calls.append((prompts, threshold, iou))
        return {'prompt_results': [
            {'prompt_index': i, 'echo': {'text': text}, 'predictions': [
                {'confidence': .9, 'masks': [[[-5, 2], [10, 2], [10, 20]], [[40, 20], [90, 20], [90, 70]]]},
            ]} for i, text in reversed(list(enumerate(prompts)))]}


def test_sam_boxes_follow_explicit_prompt_classes_and_original_bounds(monkeypatch):
    worker = Worker()
    loads = []
    monkeypatch.setattr(sam3, 'open_worker', lambda: (loads.append(1) or worker))
    adapter = sam3.SAM3Adapter()
    assert adapter.inspect() == {}
    image = np.zeros((40, 50, 3), dtype=np.uint8)
    result = adapter.predict(image, config(), ['bee', 'wasp'])
    # Multiple disconnected polygons belong to one prediction, not separate objects.
    assert result == [(0, [0., 2., 50., 38.], .9), (1, [0., 2., 50., 38.], .9)]
    assert worker.calls[0] == (['a wasp', 'a bee'], .3, .5)
    adapter.predict(image, config(), ['bee', 'wasp'])
    assert len(loads) == 1
    adapter.close()
    assert worker.closed


@pytest.mark.parametrize('results', [
    [], [{'prompt_index': -1}], [{'prompt_index': 2}],
    [{'prompt_index': True}], [{'prompt_index': 0, 'echo': {'text': 'wrong'}}],
])
def test_sam_never_guesses_class_association(results, monkeypatch):
    worker = Worker()
    monkeypatch.setattr(worker, 'predict', lambda *args: {'prompt_results': results})
    monkeypatch.setattr(sam3, 'open_worker', lambda: worker)
    with pytest.raises(InvalidInput):
        sam3.SAM3Adapter().predict(np.zeros((40, 50, 3), np.uint8), config(), ['bee', 'wasp'])


@pytest.mark.parametrize('polygons', [None, {'counts': 'rle'}, [[[float('nan'), 1], [2, 3], [4, 5]]], [[1, 2, 3]]])
def test_sam_rejects_invalid_polygon_output(polygons):
    with pytest.raises(InvalidInput): sam3.polygon_box(polygons, 50, 40)


def test_sam_skips_empty_and_degenerate_masks():
    assert sam3.polygon_box([], 50, 40) is None
    assert sam3.polygon_box([[[1, 2], [1, 2], [1, 2]]], 50, 40) is None
    assert sam3.polygon_box([[[60, 2], [80, 2], [80, 20]]], 50, 40) is None


@pytest.mark.parametrize('fail', [False, True])
def test_prompt_model_executes_through_shared_jobs_without_yolo_assumptions(tmp_path, monkeypatch, fail):
    import cv2
    from app.api import state
    from app.api.frames.service import init_frames
    from app.autolabeling import jobs, service
    from app.autolabeling.models import RunRequest
    class Inline:
        def submit(self, function, *args): function(*args)
    definition = ModelDefinition(id='demo', name='Demo', adapter='demo', source='catalog',
        description='Test provider', inputs=DemoInputs, factory=f'{__name__}:DemoAdapter',
        strategy='prompt_based', requires_checkpoint=False, required_packages=())
    state.coco_writer.flush(); state.reset_state()
    try:
        registry.DEFINITIONS['demo'] = definition
        monkeypatch.setattr(DemoAdapter, 'inspect', lambda self: {}, raising=False)
        closed = []
        def predict(self, image, config, classes):
            if fail: raise InvalidInput('Provider failed')
            return [(0, [1, 2, 3, 4], .8)]
        monkeypatch.setattr(DemoAdapter, 'predict', predict, raising=False)
        monkeypatch.setattr(DemoAdapter, 'close', lambda self: closed.append(True), raising=False)
        monkeypatch.setattr(jobs, 'executor', Inline())
        image = tmp_path/'frame.png'
        cv2.imwrite(str(image), np.zeros((30, 40, 3), np.uint8))
        output = tmp_path/'project'; output.mkdir()
        session = state.create_session(mode='detection', data_path=image, output_path=output, classes=['object'])
        init_frames()
        cfg = ModelConfig(adapter='demo', model_id='demo', parameters={'instruction': 'Find objects'})
        run = service.create_run(RunRequest(session_id=session.session_id, config=cfg))
        result = service.proposals(run['id'])
        assert result['run']['status'] == ('partially_failed' if fail else 'succeeded')
        assert closed == [True]
        if not fail: assert result['proposals'][0]['class_name'] == 'object'
        assert result['run']['model_definition']['id'] == 'demo'
        assert not state.annotation_store
    finally:
        registry.DEFINITIONS.pop('demo', None)
        state.coco_writer.flush(); state.reset_state()


def test_catalog_setup_api_is_scoped_and_keeps_checkpoint_out_of_project_preferences(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.api import state
    from app.autolabeling import service
    monkeypatch.setattr(settings.app_config, 'LOCAL_DIR', tmp_path/'settings')
    checkpoint_definition(monkeypatch)
    weights = tmp_path/'sam3.pt'; weights.write_bytes(b'weights')
    client = TestClient(app)
    response = client.get('/api/autolabeling/models?task=detect_boxes')
    assert response.status_code == 200
    assert {'ultralytics', 'sam3', 'ollama-qwen3-vl-4b', 'ollama-qwen3-vl-8b', 'ollama-gemma3-4b'} <= {item['id'] for item in response.json()}
    assert client.get('/api/autolabeling/models?task=produce_obb').json() == []
    response = client.put('/api/autolabeling/models/sam3/setup', json={'model_path': str(weights)})
    assert response.status_code == 200, response.text
    assert response.json()['setup']['model_path'] == str(weights)
    assert client.put('/api/autolabeling/models/not-registered/setup', json={'model_path': str(weights)}).status_code == 422
    output = tmp_path/'project'; output.mkdir()
    state.reset_state()
    try:
        state.create_session(mode='detection', data_path=tmp_path, output_path=output, classes=['wasp', 'bee'])
        service.save_configuration(config(model_path=str(weights)))
        assert service.configuration()['model_path'] == ''
        assert service.configuration()['model_id'] == 'sam3'
    finally:
        state.reset_state()
