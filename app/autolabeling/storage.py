"""Atomic project-local manifests; run IDs cannot be used as filesystem paths."""

import json
from pathlib import Path
from threading import RLock
from uuid import UUID

from app.api.common.errors import NotFound
from app.core.project_state.writer import write_json_atomic

storage_lock = RLock()


def root(project):
    return Path(project) / '.inolabel' / 'autolabeling'


def run_path(project, run_id):
    try:
        normalized = str(UUID(run_id))
    except (ValueError, TypeError, AttributeError):
        raise NotFound('Run not found.')
    return root(project) / 'runs' / (normalized + '.json')


def read_run(project, run_id):
    path = run_path(project, run_id)
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise NotFound('Run not found or its manifest is unreadable.')


def write_run(project, run):
    write_json_atomic(run_path(project, run['id']), run)


def list_runs(project):
    runs = []
    for path in (root(project) / 'runs').glob('*.json'):
        try:
            runs.append(json.loads(path.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            continue
    return sorted(runs, key=lambda r: r['created_at'], reverse=True)
