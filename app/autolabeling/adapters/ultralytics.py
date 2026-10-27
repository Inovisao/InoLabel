"""Translate Ultralytics detection outputs into mapped box predictions."""

import math
from pathlib import Path

from app.api.common.errors import InvalidInput
from app.core.detector import Detector


def checkpoint(path):
    value = Path(path).expanduser().resolve()
    if not value.is_file() or value.suffix.lower() != '.pt':
        raise InvalidInput('Choose an existing YOLO .pt file.')
    return value


class YoloAdapter:
    def __init__(self, path):
        self.detector = Detector(checkpoint(path))

    def inspect(self):
        model = self.detector.load()
        if getattr(model, 'task', None) != 'detect':
            raise InvalidInput('This workflow requires a YOLO detection checkpoint.')
        names = model.names
        self.names = {int(k): str(v) for k, v in (names.items() if isinstance(names, dict) else enumerate(names))}
        if not self.names or len(set(self.names.values())) != len(self.names):
            raise InvalidInput('The model must expose distinct class names.')
        return self.names

    def predict(self, image, config, classes):
        results = self.detector.predict(image, conf=config.confidence, verbose=False)
        if not results:
            return []
        height, width = image.shape[:2]
        predictions = []
        boxes = results[0].boxes
        for box in ([] if boxes is None else boxes):
            model_id = int(box.cls.item())
            target = config.class_mapping.get(self.names.get(model_id, ''))
            if target is None:
                continue
            if target not in classes:
                raise InvalidInput('A mapped class is no longer present in the project.')
            score = float(box.conf.item())
            coords = box.xyxy[0].detach().cpu().tolist()
            if not all(math.isfinite(float(x)) for x in [score, *coords]):
                raise InvalidInput('The detector returned non-finite predictions.')
            x1, y1, x2, y2 = coords
            x1, x2 = max(0., min(x1, width)), max(0., min(x2, width))
            y1, y2 = max(0., min(y1, height)), max(0., min(y2, height))
            if x2 > x1 and y2 > y1 and score >= config.confidence:
                predictions.append((classes.index(target), [x1, y1, x2-x1, y2-y1], score))
        return predictions
