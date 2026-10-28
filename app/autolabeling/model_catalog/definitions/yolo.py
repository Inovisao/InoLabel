from app.autolabeling.model_catalog.schemas import ModelDefinition, ModelInputs


DEFINITION = ModelDefinition(
    id='ultralytics', name='YOLO', adapter='ultralytics', source='imported',
    description='Importe um checkpoint de detecção e mapeie suas classes.',
    inputs=ModelInputs, factory='app.autolabeling.adapters.ultralytics:YoloAdapter',
)
