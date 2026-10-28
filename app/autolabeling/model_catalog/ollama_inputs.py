"""Prompt and generation inputs shared by local Ollama vision models."""

from typing import List

from pydantic import Field, model_validator

from app.autolabeling.model_catalog.prompt_inputs import ClassPrompt
from app.autolabeling.model_catalog.schemas import ModelInputs


class OllamaInputs(ModelInputs):
    instruction: str = Field(default='Find every visible instance of the described objects.', min_length=1, max_length=1000,
                             title='Instrução para a imagem', description='Oriente o modelo sobre o que localizar e ignorar.')
    class_prompts: List[ClassPrompt] = Field(min_length=1, max_length=32, title='Descrições por classe',
        description='Associe uma descrição visual a cada classe que deseja localizar.', json_schema_extra={'x-control': 'class-prompts'})

    def project_classes(self):
        return [item.class_name for item in self.class_prompts]

    def proposal_prompt(self, class_name):
        prompt = next(item for item in self.class_prompts if item.class_name == class_name)
        return prompt.text

    @model_validator(mode='after')
    def unique_classes(self):
        names = self.project_classes()
        if len(set(names)) != len(names):
            raise ValueError('Use uma descrição por classe nesta versão.')
        return self
