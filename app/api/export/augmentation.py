"""Augmentation na exportação: catálogo e o preset escolhido no pedido."""

from __future__ import annotations

from typing import Optional

from app.annotation.core.augmentation.augmentation_types import (
    AUGMENTATION_CATALOG,
    AugEntry,
    AugmentationPreset,
)
from app.api.common.errors import InvalidInput
from app.api.export.schemas import AugmentationOption, ExportRequest

DEFAULT_AUGMENTATIONS = ("flip_h", "brightness", "contrast")


def catalog() -> list[AugmentationOption]:
    return [AugmentationOption(key=i.key, label=i.label, description=i.description) for i in AUGMENTATION_CATALOG]


def preset_for(body: ExportRequest) -> Optional[AugmentationPreset]:
    """Preset com as augmentations pedidas (ou as padrão); None se desligado."""
    if not body.augmentation:
        return None
    by_key = {item.key: item for item in AUGMENTATION_CATALOG}
    keys = body.augmentations or list(DEFAULT_AUGMENTATIONS)
    unknown = [k for k in keys if k not in by_key]
    if unknown:
        raise InvalidInput(f"Augmentation desconhecida: {', '.join(unknown)}")
    entries = [
        AugEntry(key=k, enabled=True, params={p.key: p.default for p in by_key[k].params})
        for k in keys
    ]
    return AugmentationPreset(enabled=True, copies_per_image=body.augmentation_copies, entries=entries)
