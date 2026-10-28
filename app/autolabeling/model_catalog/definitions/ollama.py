"""Curated Ollama vision models registered as separate catalog choices."""

from app.autolabeling.model_catalog.ollama_inputs import OllamaInputs
from app.autolabeling.model_catalog.schemas import ModelDefinition
from app.autolabeling.runtimes.ollama import MODELS

DEFINITIONS = tuple(ModelDefinition(
    id=model['id'], name=model['name'], adapter='ollama', source='catalog',
    description=model['description'], inputs=OllamaInputs,
    factory='app.autolabeling.adapters.ollama:OllamaAdapter', strategy='prompt_based',
    requires_checkpoint=False, score_type='model_confidence', schema_version=model['schema_version'],
    required_packages=(), runtime_status='app.autolabeling.runtimes.ollama:model_status',
    setup_instructions='Instale e inicie o Ollama para baixar e executar modelos nesta máquina.',
    documentation_url='https://ollama.com/download', provider_model=model['tag'],
    download_size_bytes=model['size_bytes']) for model in MODELS)
