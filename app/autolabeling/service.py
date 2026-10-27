"""Submit immutable labeling jobs and commit reviewed proposals to the active project."""

import json
import math
from datetime import datetime, timezone
from uuid import uuid4

from app.api import state
from app.api.annotations import service as annotations
from app.api.annotations.project_state import save_project_state, frame_dims
from app.api.annotations.labels import write_label_file
from app.api.annotations.schemas import AnnotationUpsert
from app.api.common.errors import InvalidInput, NotFound
from app.autolabeling import jobs
from app.autolabeling.adapters.ultralytics import checkpoint
from app.autolabeling.adapters.registry import create_adapter
from app.autolabeling.models import ModelConfig
from app.autolabeling.storage import list_runs, read_run, root, storage_lock, write_run
from app.core.project_state.paths import state_path
from app.core.project_state.writer import write_json_atomic
from app.core.runtime_lock import protect_state


def _session(session_id=None):
    session = state.active_session()
    if session is None or (session_id and session.session_id != session_id):
        raise InvalidInput('Activate the project associated with this request.')
    if session.mode != 'detection':
        raise InvalidInput('Box autolabeling currently supports detection projects.')
    return session


def inspect_model(config):
    path = checkpoint(config.model_path)
    try:
        names = create_adapter(config.adapter, path).inspect()
    except InvalidInput:
        raise
    except Exception as exc:
        raise InvalidInput('Cannot load the detection model: ' + str(exc)) from exc
    return {'adapter': 'ultralytics', 'task': 'detect_boxes', 'classes': list(names.values()), 'model_path': str(path)}


@protect_state
def configuration():
    session = _session()
    path = root(session.output_path) / 'config.json'
    try:
        return ModelConfig.model_validate_json(path.read_text(encoding='utf-8')).model_dump()
    except (OSError, ValueError):
        return {'model_path': str(session.model_path or ''), 'confidence': session.confidence_threshold, 'class_mapping': {}}


@protect_state
def save_configuration(config):
    session = _session()
    config = config.model_copy(update={'model_path': str(checkpoint(config.model_path))})
    write_json_atomic(root(session.output_path) / 'config.json', config.model_dump())
    return config.model_dump()


@protect_state
def create_run(request):
    session = _session(request.session_id)
    if not state.frame_paths:
        raise InvalidInput('Initialize the project images first.')
    indices = list(range(len(state.frame_paths))) if request.frame_indices is None else request.frame_indices
    if not indices or len(set(indices)) != len(indices) or any(i < 0 or i >= len(state.frame_paths) for i in indices):
        raise InvalidInput('Select distinct image indices within the dataset.')
    if len(indices) > 10000:
        raise InvalidInput('Choose at most 10,000 images per run.')
    config = request.config.model_copy(update={'model_path': str(checkpoint(request.config.model_path))})
    if any(target is not None and target not in session.classes for target in config.class_mapping.values()):
        raise InvalidInput('The class mapping no longer matches this project.')
    if not any(target is not None for target in config.class_mapping.values()):
        raise InvalidInput('Map at least one model class before running.')
    try:
        media = [{'index': i, 'path': str(state.frame_paths[i]), 'hash': jobs.fingerprint(state.frame_paths[i])} for i in indices]
        model_hash = jobs.fingerprint(config.model_path)
    except OSError as exc:
        raise InvalidInput('Cannot snapshot the model or dataset: ' + str(exc)) from exc
    run = {'id': str(uuid4()), 'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
           'status': 'queued', 'project': str(session.output_path), 'data_path': str(session.data_path),
           'classes': list(session.classes), 'mode': session.mode, 'config': config.model_dump(),
           'model_hash': model_hash, 'media': media, 'proposals': [], 'outcomes': {}, 'error': None}
    with storage_lock:
        write_run(session.output_path, run)
    try:
        jobs.submit(session.output_path, run)
    except Exception:
        run['status'] = 'failed'
        run['error'] = 'The local execution queue is unavailable.'
        with storage_lock:
            write_run(session.output_path, run)
        raise
    save_configuration(config)
    return summary(run)


def summary(run):
    return {key: run[key] for key in ('id', 'created_at', 'status', 'error')} | {
        'total': len(run['media']), 'processed': len(run['outcomes']),
        'failed': sum(o['status'] == 'failed' for o in run['outcomes'].values()),
        'pending': sum(p['status'] == 'pending' for p in run['proposals']),
        'accepted': sum(p['status'] == 'accepted' for p in run['proposals']),
        'config': run['config'], 'outcomes': run['outcomes'],
    }


@protect_state
def runs():
    session = _session()
    with storage_lock:
        result = []
        for run in list_runs(session.output_path):
            if run['status'] in ('running', 'queued') and not jobs.is_active(session.output_path, run['id']):
                run['status'] = 'interrupted'
                write_run(session.output_path, run)
            result.append(summary(run))
        return result


@protect_state
def proposals(run_id, frame_index=None, offset=0, limit=100):
    session = _session()
    with storage_lock:
        run = read_run(session.output_path, run_id)
        matching = [p for p in run['proposals'] if frame_index is None or p['frame_index'] == frame_index]
        return {'run': summary(run), 'proposals': matching[offset:offset + limit], 'total': len(matching)}


@protect_state
def stop_run(run_id):
    session = _session()
    with storage_lock:
        run = read_run(session.output_path, run_id)
    jobs.cancel(session.output_path, run_id)
    return summary(run)


@protect_state
def resume_run(run_id):
    session = _session()
    with storage_lock:
        run = read_run(session.output_path, run_id)
        if run['status'] not in ('interrupted', 'cancelled', 'failed', 'partially_failed'):
            raise InvalidInput('Only interrupted, cancelled, or failed runs can be resumed.')
        if run['classes'] != session.classes or run['data_path'] != str(session.data_path):
            raise InvalidInput('Project inputs changed. Create a new run.')
    jobs.submit(session.output_path, run)
    return summary(run)


def _proposal(run, proposal_id):
    for proposal in run['proposals']:
        if proposal['id'] == proposal_id:
            return proposal
    raise NotFound('Proposal not found.')


def _source(run_id, proposal_id):
    return f'autolabeling:{run_id}:{proposal_id}'


def _durable(session, source, frame_index, present=True):
    width, height = frame_dims(frame_index)
    write_label_file(session, frame_index, width, height)
    save_project_state()
    if not state.coco_writer.flush(timeout=30):
        raise InvalidInput('Saving timed out. Retry to recover this operation.')
    try:
        data = json.loads(state_path(session.output_path, session.mode).read_text(encoding='utf-8'))
        saved = [a for a in data.get('annotations', []) if a.get('source') == source]
        if not present:
            if saved:
                raise ValueError('The removed annotation is still present on disk.')
        else:
            expected = next(a for a in state.annotation_store[frame_index] if a.source == source)
            if len(saved) != 1 or saved[0]['id'] != expected.id or saved[0]['category_id'] != expected.category_id + 1:
                raise ValueError('The annotation identity was not persisted.')
            if not all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(saved[0]['bbox'], expected.bbox)):
                raise ValueError('The annotation geometry was not persisted.')
    except (OSError, ValueError) as exc:
        raise InvalidInput('Could not confirm the saved operation. Retry to recover it.') from exc


@protect_state
def review(run_id, request, action):
    session = _session()
    with storage_lock:
        run = read_run(session.output_path, run_id)
        proposal = _proposal(run, request.proposal_id)
        if run['classes'] != session.classes or run['data_path'] != str(session.data_path):
            raise InvalidInput('The project classes or dataset changed. Generate new suggestions.')
        index = proposal['frame_index']
        media = next(m for m in run['media'] if m['index'] == index)
        if index >= len(state.frame_paths) or str(state.frame_paths[index]) != media['path']:
            raise InvalidInput('Dataset ordering changed. Generate new suggestions.')
        if jobs.fingerprint(media['path']) != media['hash']:
            raise InvalidInput('This image changed. Generate new suggestions.')
        outcome = run['outcomes'].get(str(index), {})
        if outcome.get('status') != 'succeeded':
            raise InvalidInput('This image has no successful prediction result.')
        state.frame_dims[index] = (outcome['width'], outcome['height'])
        annotations.ensure_loaded_from_disk(index)
        source = _source(run_id, proposal['id'])
        existing = next((a for a in state.annotation_store.get(index, []) if a.source == source), None)
        if action == 'reject':
            if existing or proposal['status'] == 'accepted':
                raise InvalidInput('Undo acceptance before rejecting this proposal.')
            proposal['status'] = 'rejected'
        elif action == 'undo':
            if proposal['status'] != 'accepted':
                raise InvalidInput('This proposal has not been accepted.')
            if existing:
                if existing.bbox != proposal.get('accepted_bbox') or existing.category_id != proposal.get('accepted_category_id'):
                    raise InvalidInput('This annotation was edited. Remove it manually to preserve your changes.')
                annotations.delete_annotation(index, existing.id)
            _durable(session, source, index, present=False)
            proposal.update(status='pending', annotation_id=None)
        else:
            if proposal['status'] == 'rejected':
                raise InvalidInput('Rejected proposals cannot be accepted. Generate a new run.')
            if proposal['status'] == 'accepted' and existing is None:
                raise InvalidInput('The accepted annotation was removed. Undo acceptance before accepting again.')
            if existing is None:
                category = request.category_id if request.category_id is not None else proposal['category_id']
                bbox = request.bbox if request.bbox is not None else proposal['bbox']
                if category >= len(session.classes) or bbox[2] <= 0 or bbox[3] <= 0:
                    raise InvalidInput('Choose a valid class and a box with positive dimensions.')
                width, height = frame_dims(index)
                x, y, w, h = bbox
                if x < 0 or y < 0 or x + w > width or y + h > height:
                    raise InvalidInput('The box must fit inside the original image.')
                existing = annotations.add_annotation(index, AnnotationUpsert(
                    category_id=category, bbox=bbox, source=source, score=proposal['score']))
            _durable(session, source, index)
            proposal.update(status='accepted', annotation_id=existing.id,
                            accepted_bbox=list(existing.bbox), accepted_category_id=existing.category_id)
        write_run(session.output_path, run)
        return {'proposal': proposal, 'annotation': existing.model_dump() if existing and action == 'accept' else None}
