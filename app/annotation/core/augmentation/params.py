"""Leitura dos parâmetros de cada augmentation (com valor padrão e probabilidade)."""

from __future__ import annotations

import numpy as np


def passes_prob(params: dict, rng: np.random.Generator) -> bool:
    return bool(rng.random() <= float_param(params, "prob", 0.5))


def float_param(params: dict, key: str, default: float) -> float:
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError):
        return default


def int_param(params: dict, key: str, default: int) -> int:
    try:
        return int(round(float(params.get(key, default))))
    except (TypeError, ValueError):
        return default
