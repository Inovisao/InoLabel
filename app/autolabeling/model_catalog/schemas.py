"""Catalog metadata and typed model-specific input contracts."""

from dataclasses import dataclass
from typing import Tuple, Type

from pydantic import BaseModel, ConfigDict


class ModelInputs(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    def project_classes(self):
        return []

    def proposal_prompt(self, class_name):
        return None


@dataclass(frozen=True)
class ModelDefinition:
    id: str
    name: str
    adapter: str
    source: str
    description: str
    inputs: Type[ModelInputs]
    factory: str
    tasks: Tuple[str, ...] = ('detect_boxes',)
    strategy: str = 'trained_model'
    requires_checkpoint: bool = True
    schema_version: int = 1
    score_type: str = 'detection_confidence'
    documentation_url: str = ''
    required_packages: Tuple[str, ...] = ('ultralytics', 'torch', 'torchvision')
    requirements_file: str = 'requirements.txt'
    required_environment: Tuple[str, ...] = ()
    runtime_status: str = ''
    preparation: str = ''
    setup_instructions: str = ''
    provider_model: str = ''
    download_size_bytes: int = 0

    def describe(self):
        return {
            'id': self.id, 'name': self.name, 'adapter': self.adapter,
            'source': self.source, 'description': self.description,
            'tasks': list(self.tasks), 'schema_version': self.schema_version,
            'strategy': self.strategy, 'requires_checkpoint': self.requires_checkpoint,
            'input_schema': self.inputs.model_json_schema(),
            'score_type': self.score_type, 'documentation_url': self.documentation_url,
            'requirements_file': self.requirements_file,
            'can_prepare': bool(self.preparation),
            'setup_instructions': self.setup_instructions,
            'provider_model': self.provider_model, 'download_size_bytes': self.download_size_bytes,
        }
