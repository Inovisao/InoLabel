"""Sessão de anotação: início, estado e fim."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.common.schemas import TaskMode


class KeypointClassSpec(BaseModel):
    """Pontos de uma classe no modo keypoint, na ordem em que são clicados.

    ``skeleton`` liga pares de pontos (índices a partir de 0, como na 1.0.0); vazio
    = os pontos são ligados em sequência.
    """

    name: str
    keypoints: List[str]
    skeleton: List[List[int]] = Field(default_factory=list)

    @field_validator("keypoints")
    @classmethod
    def keypoint_names_valid(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("Cada classe precisa de ao menos um ponto.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Nomes de pontos repetidos na mesma classe.")
        return cleaned

    @model_validator(mode="after")
    def skeleton_in_range(self) -> "KeypointClassSpec":
        n = len(self.keypoints)
        for link in self.skeleton:
            if len(link) != 2 or not all(0 <= int(i) < n for i in link) or link[0] == link[1]:
                raise ValueError(f"Ligação de esqueleto inválida para '{self.name}': {link}.")
        return self

class SessionStartRequest(BaseModel):
    mode: TaskMode
    data_path: Optional[str] = None
    output_path: Optional[str] = None
    model_path: Optional[str] = None
    resume: bool = False
    classes: List[str]
    data_root: Optional[str] = None
    output_dir: Optional[str] = None
    weights_paths: List[str] = Field(default_factory=list)
    confidence_threshold: float = 0.4
    resume_existing: bool = False
    # Modo keypoint: pontos de cada classe. Ao retomar, pode faltar (vem do projeto).
    keypoint_classes: List[KeypointClassSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_legacy_frontend_names(self) -> "SessionStartRequest":
        if self.data_path is None and self.data_root is not None:
            self.data_path = self.data_root
        if self.output_path is None and self.output_dir is not None:
            self.output_path = self.output_dir
        if self.model_path is None and self.weights_paths:
            self.model_path = self.weights_paths[0]
        self.resume = self.resume or self.resume_existing
        return self

    @model_validator(mode="after")
    def validate_mode_specific_constraints(self) -> "SessionStartRequest":
        if self.mode == TaskMode.CLASSIFICATION and len(self.classes) < 2:
            raise ValueError(
                "Modo classificação requer ao menos 2 classes. "
                "Com apenas 1 classe não é possível distinguir categorias."
            )
        return self

    @field_validator("confidence_threshold")
    @classmethod
    def confidence_threshold_in_range(cls, value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"confidence_threshold deve estar entre 0.0 e 1.0, recebeu {value}."
            )
        return value

    @field_validator("classes")
    @classmethod
    def classes_not_empty(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("Informe ao menos uma classe.")
        # Deduplicate preserving order — duplicate class names create ambiguous
        # category IDs and break YOLO export consistency.
        seen: set[str] = set()
        return [c for c in cleaned if not (c in seen or seen.add(c))]  # type: ignore[func-returns-value]

class SessionStartResponse(BaseModel):
    session_id: str
    total_frames: int
    current_frame: int
    active: bool = True
    mode: Optional[TaskMode] = None
    current_index: int = 0
    classes: List[str] = []
    autosaved: bool = False

class SessionStatusResponse(BaseModel):
    session_id: str
    current_frame: int
    total_frames: int
    saved_frames: int
    status: str

class SessionActionRequest(BaseModel):
    action: str

class SessionActionResponse(BaseModel):
    current_frame: int
    annotation_count: int

class SessionStopResponse(BaseModel):
    saved_frames: int
    output_path: str
