"""Compatibility facade over the shared model catalog."""

from app.autolabeling.model_catalog.registry import DEFINITIONS, construct_adapter


def capabilities():
    return {
        'workflows': [
            {'id': 'trained_model', 'available': True, 'tasks': ['detect_boxes']},
            {'id': 'prompt_based', 'available': True, 'tasks': ['detect_boxes']},
        ],
        'adapters': [{'id': adapter_id, 'runtime': 'local', 'tasks': ['detect_boxes']}
                     for adapter_id in dict.fromkeys(d.adapter for d in DEFINITIONS.values())],
    }


def create_adapter(adapter_id, model_path, model_id=None):
    return construct_adapter(adapter_id, model_path, model_id)
