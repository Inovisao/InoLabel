from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TaskMode(str, Enum):
    TRACKING = "tracking"
    DETECTION = "detection"
    OBB = "obb"
    CLASSIFICATION = "classification"
    KEYPOINT = "keypoint"


class ModeInfo(BaseModel):
    id: TaskMode
    label: str
    description: str
    icon: str


class PathValidationRequest(BaseModel):
    path: str


class OutputsRequest(BaseModel):
    output_path: str


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


class ProjectEntry(BaseModel):
    name: str
    path: str
    data_path: str
    mode: str
    annotated_frames: int
    classes: List[str]
    created_at: str
    last_modified: str


class KeybindProfile(BaseModel):
    profile: str
    binds: Dict[str, str]


class OBBGeometry(BaseModel):
    cx: float
    cy: float
    width: float
    height: float
    angle: float = 0.0
    angle_unit: str = "degrees"
    points: Optional[List[List[float]]] = None

    @field_validator("width", "height")
    @classmethod
    def positive_size(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("width e height devem ser maiores que zero.")
        return value

    @field_validator("angle_unit")
    @classmethod
    def angle_unit_degrees(cls, value: str) -> str:
        if value != "degrees":
            raise ValueError("angle_unit deve ser 'degrees'.")
        return value

    @field_validator("points")
    @classmethod
    def points_must_be_four_xy_pairs(
        cls, value: Optional[List[List[float]]]
    ) -> Optional[List[List[float]]]:
        if value is None:
            return value
        if len(value) != 4 or any(len(point) != 2 for point in value):
            raise ValueError("points deve conter exatamente 4 pares [x, y].")
        return value


class Annotation(BaseModel):
    id: int
    image_id: int
    category_id: int
    bbox: List[float]
    obb: Optional[OBBGeometry] = None
    track_id: Optional[int] = None
    source: str = "manual"
    score: Optional[float] = None
    # Modo keypoint: [[x, y, v], ...] na ordem da classe; v = 0 ausente, 1 oculto, 2 visível.
    keypoints: Optional[List[List[float]]] = None


class FrameResponse(BaseModel):
    index: int
    total: int
    image_b64: str
    filename: str
    annotations: List[Annotation] = []
    is_saved: bool = False
    reviewed: bool = False
    # Modo classificação: índice da classe já atribuída a esta imagem (None = não classificada).
    classification_id: Optional[int] = None


class ClassItem(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    # Modo keypoint: nomes dos pontos e esqueleto da classe.
    keypoints: List[str] = Field(default_factory=list)
    skeleton: List[List[int]] = Field(default_factory=list)


class AnnotationUpsert(BaseModel):
    category_id: int
    # No modo keypoint a bbox é calculada a partir dos pontos (pode ir [0, 0, 0, 0]).
    bbox: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    obb: Optional[OBBGeometry] = None
    track_id: Optional[int] = None
    source: str = "manual"
    score: Optional[float] = None
    keypoints: Optional[List[List[float]]] = None

    @field_validator("category_id")
    @classmethod
    def category_id_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError(
                f"category_id deve ser >= 0 (índice da classe YOLO), recebeu {value}."
            )
        return value

    @field_validator("bbox")
    @classmethod
    def bbox_must_have_four_elements(cls, value: List[float]) -> List[float]:
        if len(value) != 4:
            raise ValueError(
                f"bbox deve ter exatamente 4 elementos [x, y, w, h], recebeu {len(value)}."
            )
        return value


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


class TrackingInferenceRequest(BaseModel):
    session_id: Optional[str] = None
    frame_indices: Optional[List[int]] = None
    save_annotations: bool = True
    frame_rate: int = 30
    confidence_threshold: Optional[float] = None

    @field_validator("frame_rate")
    @classmethod
    def frame_rate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("frame_rate deve ser maior que zero.")
        return value

    @field_validator("confidence_threshold")
    @classmethod
    def optional_confidence_threshold_in_range(
        cls, value: Optional[float]
    ) -> Optional[float]:
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("confidence_threshold deve estar entre 0.0 e 1.0.")
        return value


class TrackingDetectionResult(BaseModel):
    bbox: List[float]
    class_id: int
    class_name: str
    confidence: float
    track_id: int


class TrackingFrameResult(BaseModel):
    frame_index: int
    timestamp: float
    detections: List[TrackingDetectionResult] = Field(default_factory=list)


class TrackingInferenceResponse(BaseModel):
    mode: str = "tracking"
    session_id: str
    processed_frames: int
    saved_annotations: bool
    frames: List[TrackingFrameResult] = Field(default_factory=list)


class ReviewedUpdate(BaseModel):
    """Marca a imagem como revisada sem objetos (entra no dataset como negativo)."""

    reviewed: bool = True


class FrameReviewState(BaseModel):
    image_id: int
    reviewed: bool
    annotation_count: int


class AnnotationPatch(BaseModel):
    """Campos alteráveis de uma anotação; os omitidos ficam como estão.

    ``track_id: null`` explícito remove o ID (o campo omitido não mexe nele).
    """

    category_id: Optional[int] = None
    track_id: Optional[int] = None
    bbox: Optional[List[float]] = None
    obb: Optional[OBBGeometry] = None
    keypoints: Optional[List[List[float]]] = None


class NextTrackId(BaseModel):
    next_track_id: int


class ClassificationState(BaseModel):
    image_id: int
    class_id: Optional[int] = None
    class_name: Optional[str] = None


class WorkspaceOpen(BaseModel):
    """Abre a pasta como workspace; cria o índice se ainda não for um."""

    path: str
    name: Optional[str] = None


class WorkspaceProjectRef(BaseModel):
    folder: str
    name: str
    mode: str = ""
    created_at: str = ""


class WorkspaceInfo(BaseModel):
    path: str
    name: str
    version: int = 1
    created_at: str = ""
    projects: List[WorkspaceProjectRef] = Field(default_factory=list)


class WorkspaceRecent(BaseModel):
    path: str
    name: str
    opened_at: str = ""
    exists: bool = True


class WorkspaceOverview(BaseModel):
    current: Optional[WorkspaceInfo] = None
    recent: List[WorkspaceRecent] = Field(default_factory=list)


class WorkspaceProjectCreate(BaseModel):
    workspace: str
    name: str
    mode: TaskMode
    data_path: str
    classes: List[str]


class WorkspaceProjectUpdate(BaseModel):
    workspace: str
    folder: str
    data_path: Optional[str] = None


class WorkspaceProjectCreated(BaseModel):
    folder: str
    output_path: str
