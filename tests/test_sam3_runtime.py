"""Roboflow setup isolation, worker lifecycle, protocol, and credential boundaries."""

import json
import sys
from types import SimpleNamespace

import pytest

from app.api.common.errors import InvalidInput
from app.autolabeling.model_catalog import registry, settings
from app.autolabeling.runtimes import roboflow, roboflow_worker


def test_sdk_contract_matches_roboflow_text_segmentation(monkeypatch):
    requests = []
    class Prompt:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)
    monkeypatch.setitem(sys.modules, 'inference.core.entities.requests.sam3', SimpleNamespace(Sam3Prompt=Prompt))
    def segment_image(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(model_dump=lambda **options: {'prompt_results': []})
    response = roboflow_worker.segment(SimpleNamespace(segment_image=segment_image), {
        'image': '/local/image.png', 'prompts': ['a bee'], 'score_threshold': .3, 'iou_threshold': .5,
    })
    assert response == {'prompt_results': []}
    assert requests[0]['format'] == 'polygon'
    assert requests[0]['output_prob_thresh'] == .3
    assert requests[0]['nms_iou_threshold'] == .5
    assert requests[0]['prompts'][0].type == 'text'
    assert requests[0]['prompts'][0].text == 'a bee'


def test_credentials_are_never_project_parameters_or_catalog_values(monkeypatch):
    secret = 'test-only-secret-must-not-leak'
    monkeypatch.setenv('ROBOFLOW_API_KEY', secret)
    monkeypatch.delenv('INOLABEL_SAM3_PYTHON', raising=False)
    entry = next(x for x in registry.catalog() if x['id'] == 'sam3')
    assert secret not in json.dumps(entry)
    assert not entry['requires_checkpoint'] and entry['can_prepare']
    assert entry['availability'] == 'setup_required'
    assert 'ROBOFLOW_API_KEY' not in entry['input_schema']['properties']
    with pytest.raises(InvalidInput): settings.prepare_model('ultralytics')
    with pytest.raises(InvalidInput): settings.prepare_model('unknown')


def test_missing_credentials_fail_without_starting_worker(monkeypatch):
    monkeypatch.delenv('ROBOFLOW_API_KEY', raising=False)
    monkeypatch.setattr(roboflow.subprocess, 'Popen', lambda *a, **k: pytest.fail('worker must not start'))
    with pytest.raises(InvalidInput, match='ROBOFLOW_API_KEY'):
        roboflow.WorkerClient()


def test_virtualenv_interpreter_symlink_is_preserved(tmp_path, monkeypatch):
    path = tmp_path/'python'; path.symlink_to(sys.executable)
    monkeypatch.setenv('INOLABEL_SAM3_PYTHON', str(path))
    assert roboflow.executable() == path


def test_prepare_validates_cache_and_invalidates_changed_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(roboflow.app_config, 'LOCAL_DIR', tmp_path/'local')
    monkeypatch.setenv('INOLABEL_SAM3_PYTHON', sys.executable)
    info = {'packages': {'inference-gpu': '1.1.2'}}
    monkeypatch.setattr(roboflow, 'runtime_info', lambda: info)
    cache = roboflow.runtime_directory()/'cache'/'sam3'/'sam3_final'
    cache.mkdir(parents=True)
    artifacts = [cache/'weights.pt', cache/'bpe_simple_vocab_16e6.txt.gz']
    for path in artifacts: path.write_bytes(b'fake artifact')
    clients = []
    class Client:
        def __init__(self, *args, **kwargs):
            self.ready = {'artifacts': [str(p) for p in artifacts]}
            self.closed = False
            clients.append(self)
        def close(self): self.closed = True
    monkeypatch.setattr(roboflow, 'WorkerClient', Client)
    assert roboflow.status()['reasons']
    roboflow.prepare()
    assert clients[0].closed
    assert roboflow.status()['reasons'] == []
    assert roboflow.prepared_record(info)['model_id'] == 'sam3/sam3_final'
    artifacts[0].write_bytes(b'changed')
    assert roboflow.status()['reasons']
    with pytest.raises(InvalidInput): roboflow.open_worker()


def test_failed_prepare_releases_lock_and_leaves_no_success_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(roboflow.app_config, 'LOCAL_DIR', tmp_path)
    monkeypatch.setattr(roboflow, 'runtime_info', lambda: {})
    def fail(*args, **kwargs): raise InvalidInput('failed')
    monkeypatch.setattr(roboflow, 'WorkerClient', fail)
    with pytest.raises(InvalidInput): roboflow.prepare()
    assert not roboflow.preparation_lock.locked()
    assert not (roboflow.runtime_directory()/'prepared.json').exists()


def test_worker_protocol_reuses_process_and_hides_sdk_stderr(tmp_path, monkeypatch):
    # A real subprocess exercises pipe buffering, initialization, and termination.
    script = tmp_path/'fake_worker.py'
    script.write_text('''import json, sys
print('SDK log with secret-api-key', file=sys.stderr, flush=True)
print('INOLABEL_SAM3 '+json.dumps({'ok': True, 'artifacts': []}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    print('INOLABEL_SAM3 '+json.dumps({'ok': True, 'response': {'prompt_results': [], 'image': request['image']}}), flush=True)
''')
    monkeypatch.setenv('ROBOFLOW_API_KEY', 'secret-api-key')
    monkeypatch.setattr(roboflow, 'worker_command', lambda mode: [sys.executable, '-u', str(script)])
    client = roboflow.WorkerClient(timeout=5)
    process = client.process
    try:
        assert client.predict('/local/image.png', ['dog'], .3, .5)['prompt_results'] == []
        assert client.predict('/local/other.png', ['cat'], .3, .5)['image'] == '/local/other.png'
        assert client.process is process
    finally:
        client.close()
    assert process.poll() is not None


def test_worker_initialization_failure_redacts_provider_errors(tmp_path, monkeypatch):
    script = tmp_path/'bad_worker.py'
    script.write_text("import sys\nprint('secret-api-key', file=sys.stderr)\nprint('INOLABEL_SAM3 {\\\"ok\\\":false}', flush=True)\n")
    monkeypatch.setenv('ROBOFLOW_API_KEY', 'secret-api-key')
    monkeypatch.setattr(roboflow, 'worker_command', lambda mode: [sys.executable, str(script)])
    with pytest.raises(InvalidInput) as error: roboflow.WorkerClient(timeout=5)
    assert 'secret-api-key' not in str(error.value)


def test_http_preparation_uses_provider_hook_and_returns_catalog_metadata(monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import app
    calls = []
    monkeypatch.setenv('ROBOFLOW_API_KEY', 'private-test-key')
    monkeypatch.setenv('INOLABEL_SAM3_PYTHON', sys.executable)
    monkeypatch.setattr(roboflow, 'prepare', lambda: calls.append(True))
    monkeypatch.setattr(roboflow, 'status', lambda model_id=None: {'reasons': [], 'snapshot': {'model_id': roboflow.MODEL_ID}})
    client = TestClient(app)
    response = client.post('/api/autolabeling/models/sam3/prepare')
    assert response.status_code == 200, response.text
    assert response.json()['availability'] == 'configured'
    assert response.json()['can_prepare'] is True
    assert response.json()['requires_checkpoint'] is False
    assert 'private-test-key' not in response.text
    assert calls == [True]
    assert client.post('/api/autolabeling/models/unknown/prepare').status_code == 422
    assert client.post('/api/autolabeling/models/ultralytics/prepare').status_code == 422
    assert calls == [True]
