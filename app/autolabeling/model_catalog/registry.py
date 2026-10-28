"""One registration per integration supplies metadata, validation, and construction."""

from importlib import import_module

from app.api.common.errors import InvalidInput
from app.autolabeling.model_catalog.definitions.yolo import DEFINITION as YOLO
from app.autolabeling.model_catalog.definitions.sam3 import DEFINITION as SAM3
from app.autolabeling.model_catalog.definitions.ollama import DEFINITIONS as OLLAMA

DEFINITIONS = {definition.id: definition for definition in (YOLO, SAM3, *OLLAMA)}


def definition_for(model_id):
    try:
        return DEFINITIONS[model_id]
    except KeyError:
        raise InvalidInput('This model integration is not registered.')


def construct_adapter(adapter_id, model_path, model_id=None):
    definition = DEFINITIONS.get(model_id) if model_id else next((d for d in DEFINITIONS.values() if d.adapter == adapter_id), None)
    if definition is None:
        raise InvalidInput('This labeling adapter is not installed.')
    module, name = definition.factory.split(':', 1)
    return getattr(import_module(module), name)(model_path)


def catalog(task='detect_boxes'):
    from app.autolabeling.model_catalog.settings import model_status
    return [{**definition.describe(), **model_status(definition)}
            for definition in DEFINITIONS.values() if task in definition.tasks]
