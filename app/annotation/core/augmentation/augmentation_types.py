"""Types and canonical catalogue of data augmentation operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class AugParamDef:
    key: str
    kind: str
    min: float
    max: float
    default: Any


@dataclass(frozen=True)
class AugCatalogItem:
    key: str
    label: str
    category: str
    description: str
    params: List[AugParamDef]


@dataclass
class AugEntry:
    key: str
    enabled: bool
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AugmentationPreset:
    enabled: bool
    copies_per_image: int
    entries: List[AugEntry] = field(default_factory=list)


AUGMENTATION_CATALOG: List[AugCatalogItem] = [
    AugCatalogItem(
        key="flip_h",
        label="Flip Horizontal",
        category="Geometrica",
        description="Espelha a imagem no eixo horizontal.",
        params=[AugParamDef("prob", "float", 0.0, 1.0, 0.5)],
    ),
    AugCatalogItem(
        key="flip_v",
        label="Flip Vertical",
        category="Geometrica",
        description="Espelha a imagem no eixo vertical.",
        params=[AugParamDef("prob", "float", 0.0, 1.0, 0.5)],
    ),
    AugCatalogItem(
        key="rotate",
        label="Rotacao",
        category="Geometrica",
        description="Rotaciona mantendo o mesmo tamanho final.",
        params=[
            AugParamDef("max_degrees", "float", 0, 45, 15),
            AugParamDef("prob", "float", 0.0, 1.0, 0.5),
        ],
    ),
    AugCatalogItem(
        key="shear",
        label="Shear",
        category="Geometrica",
        description="Inclina a imagem e recalcula as caixas.",
        params=[
            AugParamDef("max_degrees", "float", 0, 30, 10),
            AugParamDef("prob", "float", 0.0, 1.0, 0.5),
        ],
    ),
    AugCatalogItem(
        key="brightness",
        label="Brilho",
        category="Cor / aparencia",
        description="Altera a intensidade luminosa.",
        params=[AugParamDef("range_pct", "float", 0, 50, 20)],
    ),
    AugCatalogItem(
        key="contrast",
        label="Contraste",
        category="Cor / aparencia",
        description="Aumenta ou reduz o contraste.",
        params=[AugParamDef("range_pct", "float", 0, 50, 20)],
    ),
    AugCatalogItem(
        key="saturation",
        label="Saturacao",
        category="Cor / aparencia",
        description="Altera a saturacao no espaco HSV.",
        params=[AugParamDef("range_pct", "float", 0, 50, 30)],
    ),
    AugCatalogItem(
        key="hue",
        label="Matiz (Hue)",
        category="Cor / aparencia",
        description="Desloca a matiz no espaco HSV.",
        params=[AugParamDef("max_shift", "float", 0, 30, 10)],
    ),
    AugCatalogItem(
        key="grayscale",
        label="Escala de cinza",
        category="Cor / aparencia",
        description="Converte para cinza mantendo tres canais.",
        params=[AugParamDef("prob", "float", 0.0, 1.0, 0.15)],
    ),
    AugCatalogItem(
        key="blur",
        label="Desfoque Gaussiano",
        category="Ruido / blur",
        description="Aplica blur gaussiano leve.",
        params=[AugParamDef("max_kernel", "int", 1, 9, 3)],
    ),
    AugCatalogItem(
        key="noise",
        label="Ruido Gaussiano",
        category="Ruido / blur",
        description="Adiciona ruido gaussiano.",
        params=[AugParamDef("max_sigma", "float", 0, 50, 10)],
    ),
    AugCatalogItem(
        key="crop",
        label="Recorte Aleatorio",
        category="Recorte / mascaramento",
        description="Recorta uma area e reescala as caixas restantes.",
        params=[
            AugParamDef("min_area_pct", "float", 60, 95, 80),
            AugParamDef("prob", "float", 0.0, 1.0, 0.5),
        ],
    ),
    AugCatalogItem(
        key="cutout",
        label="Cutout",
        category="Recorte / mascaramento",
        description="Mascara pequenos blocos aleatorios.",
        params=[
            AugParamDef("num_patches", "int", 1, 8, 3),
            AugParamDef("max_size_pct", "float", 5, 30, 15),
        ],
    ),
]


CATALOG_BY_KEY = {item.key: item for item in AUGMENTATION_CATALOG}
