"""Exportação do dataset."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SplitConfig(BaseModel):
    train: float = 0.7
    val: float = 0.2
    test: float = 0.1

class ExportRequest(BaseModel):
    session_id: str
    destination: str
    name: str
    formats: List[str]
    split: SplitConfig = Field(default_factory=SplitConfig)
    use_split: bool = True
    augmentation: bool = False
    # Chaves do catálogo de augmentation (GET /api/export/augmentations); vazio = conjunto padrão.
    augmentations: List[str] = Field(default_factory=list)
    augmentation_copies: int = Field(default=1, ge=1, le=5)
    # COCO: "roboflow" = imagens ao lado do _annotations.coco.json; "images_dir" = em images/.
    coco_layout: Literal["roboflow", "images_dir"] = "roboflow"
    # Gera também <destination>/<name>.zip com imagens e anotações, conferindo as referências.
    zip: bool = False

class AugmentationOption(BaseModel):
    key: str
    label: str
    description: str

class ExportStartResponse(BaseModel):
    export_id: str

class ExportProgressResponse(BaseModel):
    export_id: str
    progress: float
    current_file: str
    status: str
    output_path: Optional[str] = None
    zip_path: Optional[str] = None
