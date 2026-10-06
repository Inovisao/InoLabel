"""Leitura da saída do detector (Ultralytics): caixas, confiança e classe da sessão."""

from __future__ import annotations

import numpy as np

from app.core.detector import Detector


def _scalar(value) -> float:
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    arr = np.asarray(value)
    return float(arr.reshape(-1)[0])


def _xyxy(box) -> np.ndarray:
    value = box.xyxy
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    arr = np.asarray(value, dtype=np.float32)
    return arr.reshape(-1, 4)[0].astype(np.float32)


def _class_name(names, cls_id: int, fallback_classes: list[str]) -> str:
    if isinstance(names, dict):
        raw = names.get(cls_id)
        if raw is not None:
            return str(raw)
    elif isinstance(names, list) and 0 <= cls_id < len(names):
        return str(names[cls_id])
    if 0 <= cls_id < len(fallback_classes):
        return fallback_classes[cls_id]
    return str(cls_id)


def _category_id(class_name: str, cls_id: int, classes: list[str]) -> int | None:
    for index, candidate in enumerate(classes):
        if class_name == candidate or class_name.casefold() == candidate.casefold():
            return index
    if 0 <= cls_id < len(classes):
        return cls_id
    return None


def extract_detections(detector: Detector, frame: np.ndarray, classes: list[str], conf_threshold: float):
    results = detector.predict(frame, verbose=False, conf=conf_threshold)
    if not results:
        return [], [], [], []
    result = results[0]
    names = getattr(result, "names", {})
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        boxes = []

    dets: list[np.ndarray] = []
    scores: list[float] = []
    category_ids: list[int] = []
    class_names: list[str] = []

    for box in boxes:
        confidence = _scalar(getattr(box, "conf", 0.0))
        if confidence < conf_threshold:
            continue
        cls_id = int(_scalar(getattr(box, "cls", -1)))
        class_name = _class_name(names, cls_id, classes)
        category_id = _category_id(class_name, cls_id, classes)
        if category_id is None:
            continue
        dets.append(_xyxy(box))
        scores.append(confidence)
        category_ids.append(category_id)
        class_names.append(classes[category_id])

    return dets, scores, category_ids, class_names
