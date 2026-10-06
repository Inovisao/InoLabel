"""Modo classificação."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ClassificationUpsert(BaseModel):
    category_id: int
    move_file: bool = False

    @field_validator("category_id")
    @classmethod
    def category_id_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError(
                f"category_id deve ser >= 0 (indice da classe), recebeu {value}."
            )
        return value

class ClassificationResult(BaseModel):
    image_id: int
    filename: str
    top1_class_id: int
    top1_class_name: str
    top1_confidence: Optional[float] = None
    top_k: List[dict] = Field(default_factory=list)
    destination_path: str
    operation: str

class ClassificationState(BaseModel):
    image_id: int
    class_id: Optional[int] = None
    class_name: Optional[str] = None
