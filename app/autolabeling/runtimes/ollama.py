"""Curated local Ollama catalog, model inventory, and background pull jobs."""

import json
import threading
import time
import urllib.error
import urllib.request
from uuid import uuid4

from app.api.common.errors import InvalidInput
from app.autolabeling.adapters.ollama import ollama_base_url

MODELS = (
    {'id': 'ollama-qwen3-vl-4b', 'name': 'Qwen3-VL 4B · Ollama', 'tag': 'qwen3-vl:4b', 'size_bytes': 3_300_000_000,
     'description': 'Modelo de visão compacto para testar prompts e propostas de caixas.', 'schema_version': 1},
    {'id': 'ollama-qwen3-vl-8b', 'name': 'Qwen3-VL 8B · Ollama', 'tag': 'qwen3-vl:8b', 'size_bytes': 6_200_000_000,
     'description': 'Modelo de visão com grounding 2D para propostas por descrição.', 'schema_version': 1},
    {'id': 'ollama-gemma3-4b', 'name': 'Gemma 3 4B · Ollama', 'tag': 'gemma3:4b', 'size_bytes': 3_400_000_000,
     'description': 'Modelo de visão compacto para comparar compreensão visual.', 'schema_version': 1},
)
_lock = threading.RLock()
_jobs = {}
_inventory = {'at': 0., 'models': None}


def request_json(path, payload=None, timeout=5):
    request = urllib.request.Request(ollama_base_url() + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={} if payload is None else {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def installed_models():
    now = time.monotonic()
    with _lock:
        if now - _inventory['at'] < 2:
            return _inventory['models']
    try:
        models = {item['name']: item for item in request_json('/api/tags').get('models', [])}
    except (OSError, urllib.error.URLError, InvalidInput, ValueError, KeyError):
        models = None
    with _lock:
        _inventory.update(at=now, models=models)
    return models


def model_status(model_id):
    item = next((entry for entry in MODELS if entry['id'] == model_id), None)
    installed = installed_models()
    if item is None:
        return {'reasons': ['Modelo não encontrado no catálogo Ollama.']}
    if installed is None:
        return {'reasons': ['Inicie o Ollama local para listar e baixar modelos.'], 'installed': False,
                'provider_available': False, 'provider_model': item['tag'], 'download_size_bytes': item['size_bytes']}
    present = item['tag'] in installed
    return {'reasons': [] if present else ['Baixe este modelo no Ollama para habilitar inferência.'],
            'installed': present, 'provider_available': True, 'provider_model': item['tag'], 'download_size_bytes': item['size_bytes'],
            'installed_size_bytes': installed[item['tag']]['size'] if present else None}


def catalog():
    installed = installed_models()
    return [{**item, 'installed': installed is not None and item['tag'] in installed,
             'available': installed is not None,
             'installed_size': installed[item['tag']]['size'] if installed is not None and item['tag'] in installed else None}
            for item in MODELS]


def _download(job_id, tag):
    with _lock:
        _jobs[job_id]['status'] = 'running'
    try:
        request = urllib.request.Request(ollama_base_url() + '/api/pull',
            data=json.dumps({'model': tag, 'stream': True}).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=3600) as response:
            for line in response:
                if not line.strip():
                    continue
                update = json.loads(line)
                if update.get('error'):
                    raise RuntimeError('Ollama model download failed')
                with _lock:
                    _jobs[job_id].update(status='running', progress=update.get('status', 'Downloading'),
                        completed=update.get('completed', _jobs[job_id]['completed']),
                        total=update.get('total', _jobs[job_id]['total']))
        with _lock:
            _jobs[job_id].update(status='succeeded', progress='success', completed=_jobs[job_id]['total'] or 0)
    except Exception as exc:
        with _lock:
            _jobs[job_id].update(status='failed', error=type(exc).__name__)


def start_download(model_id):
    item = next((model for model in MODELS if model['id'] == model_id), None)
    if item is None:
        raise InvalidInput('This Ollama model is not in the approved catalog.')
    installed = installed_models()
    if installed is None:
        raise InvalidInput('Start Ollama before downloading a model.')
    if item['tag'] in installed:
        return {'id': str(uuid4()), 'status': 'succeeded', 'model_id': model_id,
                'progress': 'Already installed', 'completed': item['size_bytes'], 'total': item['size_bytes']}
    with _lock:
        current = next((job for job in _jobs.values() if job['model_id'] == model_id and job['status'] in ('queued', 'running')), None)
        if current:
            return dict(current)
        job_id = str(uuid4())
        job = {'id': job_id, 'model_id': model_id, 'tag': item['tag'], 'status': 'queued',
               'progress': 'Queued', 'completed': 0, 'total': item['size_bytes'], 'error': None}
        _jobs[job_id] = job
        threading.Thread(target=_download, args=(job_id, item['tag']), daemon=True).start()
        return dict(job)


def download_status(job_id):
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
