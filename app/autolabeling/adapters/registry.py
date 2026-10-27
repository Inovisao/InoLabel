"""Explicit adapter discovery without loading models or optional SDKs."""

from app.api.common.errors import InvalidInput
from app.autolabeling.adapters.ultralytics import YoloAdapter


def capabilities():
    return {
        'workflows': [
            {'id': 'trained_model', 'available': True, 'tasks': ['detect_boxes']},
            {'id': 'prompt_based', 'available': False, 'tasks': []},
        ],
        'adapters': [
            {'id': 'ultralytics', 'runtime': 'local', 'tasks': ['detect_boxes']},
        ],
    }


def create_adapter(adapter_id, model_path):
    if adapter_id == 'ultralytics':
        return YoloAdapter(model_path)
    raise InvalidInput('This labeling adapter is not installed.')
