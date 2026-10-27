"""Bounded local execution over immutable image inputs, independent of UI sessions."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock
from uuid import uuid4

import cv2

from app.api.common.errors import InvalidInput
from app.autolabeling.adapters.registry import create_adapter
from app.autolabeling.models import ModelConfig, Proposal
from app.autolabeling.storage import read_run, storage_lock, write_run

executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='autolabeling')
execution_lock = Lock()
active_jobs = {}


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def submit(project, run):
    global executor
    key = (str(project), run['id'])
    with execution_lock:
        if key in active_jobs:
            raise InvalidInput('This run is already queued or running.')
        if len(active_jobs) >= 4:
            raise InvalidInput('The local queue is full. Wait for a run to finish.')
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="autolabeling")
        stop = Event()
        active_jobs[key] = stop
    try:
        executor.submit(_execute, project, run['id'], stop)
    except Exception:
        with execution_lock:
            active_jobs.pop(key, None)
        raise


def cancel(project, run_id):
    with execution_lock:
        stop = active_jobs.get((str(project), run_id))
        if stop:
            stop.set()
    return stop is not None


def is_active(project, run_id):
    with execution_lock:
        return (str(project), run_id) in active_jobs


def _execute(project, run_id, stop):
    try:
        with storage_lock:
            run = read_run(project, run_id)
            run.update(status='running', error=None)
            write_run(project, run)
        if stop.is_set():
            with storage_lock:
                run['status'] = 'cancelled'
                write_run(project, run)
            return
        config = ModelConfig.model_validate(run['config'])
        if fingerprint(config.model_path) != run['model_hash']:
            raise InvalidInput('The checkpoint changed. Create a new run.')
        adapter = create_adapter(config.adapter, config.model_path)
        names = adapter.inspect()
        if set(config.class_mapping) - set(names.values()):
            raise InvalidInput('The mapping contains classes not present in this model.')
        if not any(v in run['classes'] for v in config.class_mapping.values() if v is not None):
            raise InvalidInput('Map at least one model class to a project class.')
        for media in run['media']:
            if stop.is_set():
                break
            with storage_lock:
                current = read_run(project, run_id)
                if current['outcomes'].get(str(media['index']), {}).get('status') == 'succeeded':
                    continue
            try:
                if fingerprint(media['path']) != media['hash']:
                    raise InvalidInput('The input image changed. Create a new run.')
                image = cv2.imread(media['path'])
                if image is None:
                    raise InvalidInput('The image could not be read.')
                predictions = adapter.predict(image, config, run['classes'])
                proposals = [Proposal(id=str(uuid4()), frame_index=media['index'],
                                      category_id=cat, class_name=run['classes'][cat],
                                      bbox=bbox, score=score).model_dump()
                             for cat, bbox, score in predictions]
                outcome = {'status': 'succeeded', 'count': len(proposals), 'width': image.shape[1], 'height': image.shape[0]}
            except Exception as exc:
                proposals = []
                outcome = {'status': 'failed', 'error': type(exc).__name__ + ': ' + str(exc)}
            with storage_lock:
                current = read_run(project, run_id)
                current['proposals'].extend(proposals)
                current['outcomes'][str(media['index'])] = outcome
                write_run(project, current)
        with storage_lock:
            current = read_run(project, run_id)
            failed = any(o['status'] == 'failed' for o in current['outcomes'].values())
            current['status'] = 'cancelled' if stop.is_set() else ('partially_failed' if failed else 'succeeded')
            current['finished_at'] = datetime.now(timezone.utc).isoformat()
            write_run(project, current)
    except Exception as exc:
        with storage_lock:
            current = read_run(project, run_id)
            current.update(status='failed', error=type(exc).__name__ + ': ' + str(exc))
            write_run(project, current)
    finally:
        with execution_lock:
            active_jobs.pop((str(project), run_id), None)


def shutdown():
    """Stop scheduling frames and allow the current inference operation to finish."""
    global executor
    with execution_lock:
        for stop in active_jobs.values():
            stop.set()
        current = executor
        executor = None
    if current is not None:
        current.shutdown(wait=False, cancel_futures=True)
