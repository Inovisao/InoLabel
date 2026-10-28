"""Resolve saved model references and validate project-specific class bindings."""

import os

from app.api.common.errors import InvalidInput
from app.autolabeling.model_catalog.registry import definition_for
from app.autolabeling.model_catalog.settings import read_setup, resolve_checkpoint, integration_hook


def definition_of(config):
    return definition_for(config.model_id or config.adapter)


def resolve_config(config, classes=None):
    definition = definition_of(config)
    if 'detect_boxes' not in definition.tasks:
        raise InvalidInput('Este modelo não é compatível com detecção.')
    if definition.requires_checkpoint:
        reference = config.model_path or read_setup(definition.id)['model_path']
        if not reference:
            raise InvalidInput('Configure os pesos deste modelo antes de executar.')
        config = config.model_copy(update={'model_path': str(resolve_checkpoint(reference))})
    elif definition.provider_model:
        config = config.model_copy(update={'model_path': definition.provider_model})
    if classes is not None:
        validate_project_classes(config, classes)
    return config, definition


def validate_project_classes(config, classes):
    definition = definition_of(config)
    if definition.strategy == 'trained_model':
        targets = [name for name in config.class_mapping.values() if name is not None]
        if not targets:
            raise InvalidInput('Map at least one model class before running.')
    else:
        targets = definition.inputs.model_validate(config.parameters).project_classes()
        if not targets:
            raise InvalidInput('Selecione ao menos uma classe para este modelo.')
    if any(name not in classes for name in targets):
        raise InvalidInput('The class mapping or prompts no longer match this project.')


def validate_model_vocabulary(config, names):
    if definition_of(config).strategy == 'trained_model' and set(config.class_mapping) - set(names.values()):
        raise InvalidInput('The mapping contains classes not present in this model.')


def runtime_snapshot(definition):
    missing = [name for name in definition.required_environment if not os.environ.get(name)]
    if missing:
        raise InvalidInput('Configure as variáveis do servidor: ' + ', '.join(missing))
    if not definition.runtime_status:
        return None
    result = integration_hook(definition.runtime_status)(definition.id)
    if result['reasons']:
        raise InvalidInput(' '.join(result['reasons']))
    return result.get('snapshot')
