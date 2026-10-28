"""Reusable class-bound text prompts for open-vocabulary detection adapters."""

from typing import List

from pydantic import Field, field_validator, model_validator

from app.autolabeling.model_catalog.schemas import ModelInputs


class ClassPrompt(ModelInputs):
    class_name: str = Field(min_length=1, max_length=200, title='Classe')
    text: str = Field(min_length=1, max_length=300, title='Descrição')

    @field_validator('class_name', 'text')
    @classmethod
    def trim_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Informe uma classe e uma descrição não vazias.')
        return value


class ClassPromptInputs(ModelInputs):
    class_prompts: List[ClassPrompt] = Field(
        min_length=1, max_length=32, title='Descrições por classe',
        description='Use conceitos visuais curtos, como “wasp” ou “red apple”.',
        json_schema_extra={'x-control': 'class-prompts'},
    )

    def project_classes(self):
        return [prompt.class_name for prompt in self.class_prompts]

    def proposal_prompt(self, class_name):
        return next((prompt.text for prompt in self.class_prompts if prompt.class_name == class_name), None)

    @model_validator(mode='after')
    def unique_classes(self):
        names = self.project_classes()
        if len(set(names)) != len(names):
            raise ValueError('Use uma descrição por classe nesta versão.')
        return self
