from pydantic import Field

from app.autolabeling.model_catalog.schemas import ModelDefinition
from app.autolabeling.model_catalog.prompt_inputs import ClassPromptInputs


class SAM3Inputs(ClassPromptInputs):
    score_threshold: float = Field(default=0.3, ge=0, le=1, title='Score mínimo', json_schema_extra={'x-step': 0.05})
    iou_threshold: float = Field(default=0.5, ge=0, le=1, title='Limiar de sobreposição (IoU)', json_schema_extra={'x-step': 0.05})


DEFINITION = ModelDefinition(
    id='sam3', name='SAM 3', adapter='sam3', source='catalog',
    description='Encontre objetos por descrição e gere sugestões de caixas.',
    inputs=SAM3Inputs, factory='app.autolabeling.adapters.sam3:SAM3Adapter',
    strategy='prompt_based', score_type='concept_detection_score',
    requires_checkpoint=False, schema_version=2, required_packages=(),
    required_environment=('ROBOFLOW_API_KEY', 'INOLABEL_SAM3_PYTHON'),
    runtime_status='app.autolabeling.runtimes.roboflow:status',
    preparation='app.autolabeling.runtimes.roboflow:prepare',
    setup_instructions='Instale requirements-sam3.txt em um ambiente Python 3.12 separado. '
                       'Antes de abrir o aplicativo, defina INOLABEL_SAM3_PYTHON com o caminho do Python '
                       'desse ambiente e ROBOFLOW_API_KEY com sua chave privada autorizada.',
    requirements_file='requirements-sam3.txt',
    documentation_url='https://roboflow.com/blog/download-sam-3-weights',
)
