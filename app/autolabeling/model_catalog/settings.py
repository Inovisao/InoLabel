"""Local model setup, stored separately from project prompts and run snapshots."""

import os
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from threading import RLock

from pydantic import BaseModel, ConfigDict

from app import config as app_config
from app.api.common.errors import InvalidInput
from app.core.project_state.writer import write_json_atomic

settings_lock = RLock()


class ModelSetup(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model_path: str


def setup_path(model_id):
    from app.autolabeling.model_catalog.registry import definition_for
    definition_for(model_id)
    return app_config.LOCAL_DIR / 'autolabeling' / 'models' / f'{model_id}.json'


def read_setup(model_id):
    try:
        return ModelSetup.model_validate_json(setup_path(model_id).read_text(encoding='utf-8')).model_dump()
    except (OSError, ValueError):
        return {'model_path': ''}


def resolve_checkpoint(path):
    value = Path(path).expanduser().resolve()
    if not value.is_file() or value.suffix.lower() != '.pt':
        raise InvalidInput('Escolha um checkpoint .pt existente e de origem confiável.')
    return value


def save_setup(model_id, setup):
    from app.autolabeling.model_catalog.registry import definition_for
    definition = definition_for(model_id)
    if definition.source != 'catalog' or not definition.requires_checkpoint:
        raise InvalidInput('Imported checkpoints are configured in the project.')
    value = {'model_path': str(resolve_checkpoint(setup.model_path))}
    with settings_lock:
        write_json_atomic(setup_path(model_id), value)
    return {**definition.describe(), **model_status(definition)}


def integration_hook(reference):
    module, name = reference.split(':', 1)
    return getattr(import_module(module), name)


def prepare_model(model_id):
    from app.autolabeling.model_catalog.registry import definition_for
    definition = definition_for(model_id)
    if not definition.preparation:
        raise InvalidInput('Este modelo não possui uma etapa de preparação.')
    integration_hook(definition.preparation)()
    return {**definition.describe(), **model_status(definition)}


def model_status(definition):
    setup = read_setup(definition.id) if definition.source == 'catalog' and definition.requires_checkpoint else {'model_path': ''}
    reasons = []
    for package in definition.required_packages:
        try:
            version(package)
        except PackageNotFoundError:
            reasons.append(f'Dependência ausente: {package}.')
    missing_environment = [variable for variable in definition.required_environment if not os.environ.get(variable)]
    reasons.extend(f'Configure a variável {variable} no servidor.' for variable in missing_environment)
    if definition.source == 'catalog' and definition.requires_checkpoint and not Path(setup['model_path']).is_file():
        reasons.append('Configure os pesos locais obtidos na página oficial do modelo.')
    status = {}
    if definition.runtime_status and not missing_environment:
        status = integration_hook(definition.runtime_status)(definition.id)
        reasons.extend(status['reasons'])
    return {'availability': 'setup_required' if reasons else 'configured', 'reasons': reasons,
            'setup': setup, 'verified': not reasons,
            **({k: v for k, v in status.items() if k != 'reasons'} if definition.runtime_status else {})}
