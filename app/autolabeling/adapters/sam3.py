"""SAM 3 text prompts through local Roboflow Inference; polygons become box proposals."""

import math
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np

from app.api.common.errors import InvalidInput
from app.autolabeling.model_catalog.definitions.sam3 import SAM3Inputs
from app.autolabeling.runtimes.roboflow import open_worker


def polygon_box(polygons, width, height):
    points = []
    if not isinstance(polygons, list):
        raise InvalidInput('SAM 3 retornou máscaras em formato inesperado.')
    for polygon in polygons:
        try:
            coords = np.asarray(polygon, dtype=float)
        except (TypeError, ValueError):
            raise InvalidInput('SAM 3 retornou coordenadas inválidas.') from None
        if coords.size == 0:
            continue
        if coords.ndim != 2 or coords.shape[1] != 2 or not np.isfinite(coords).all():
            raise InvalidInput('SAM 3 retornou coordenadas inválidas.')
        if len(coords) >= 3:
            points.extend(coords.tolist())
    if not points:
        return None
    coords = np.asarray(points)
    x1, y1 = np.maximum(coords.min(axis=0), [0., 0.])
    x2, y2 = np.minimum(coords.max(axis=0), [width, height])
    return [float(x1), float(y1), float(x2-x1), float(y2-y1)] if x2 > x1 and y2 > y1 else None


class SAM3Adapter:
    def __init__(self, path=''):
        self.worker = None

    def inspect(self):
        return {}

    def close(self):
        if self.worker is not None:
            self.worker.close()
            self.worker = None

    def predict(self, image, config, classes):
        parameters = SAM3Inputs.model_validate(config.parameters)
        prompts = parameters.class_prompts
        if any(prompt.class_name not in classes for prompt in prompts):
            raise InvalidInput('Uma classe dos prompts não existe mais neste projeto.')
        if self.worker is None:
            self.worker = open_worker()
        # Local PNG preserves the BGR image contract without exposing dataset paths.
        with TemporaryDirectory(prefix='inolabel-sam3-') as directory:
            image_path = Path(directory) / 'image.png'
            if not cv2.imwrite(str(image_path), image):
                raise InvalidInput('Não foi possível preparar a imagem para o SAM 3.')
            response = self.worker.predict(image_path, [p.text for p in prompts],
                                           parameters.score_threshold, parameters.iou_threshold)
        height, width = image.shape[:2]
        predictions = []
        seen = set()
        for result in response['prompt_results']:
            index = result['prompt_index']
            if type(index) is not int or index < 0 or index >= len(prompts) or index in seen:
                raise InvalidInput('SAM 3 retornou uma associação de prompt inválida.')
            seen.add(index)
            if result.get('echo', {}).get('text') != prompts[index].text:
                raise InvalidInput('SAM 3 retornou uma descrição diferente do prompt enviado.')
            for prediction in result['predictions']:
                score = float(prediction['confidence'])
                if not math.isfinite(score) or not 0 <= score <= 1:
                    raise InvalidInput('SAM 3 retornou um score inválido.')
                bbox = polygon_box(prediction['masks'], width, height)
                if bbox and score >= parameters.score_threshold:
                    predictions.append((classes.index(prompts[index].class_name), bbox, score))
        if seen != set(range(len(prompts))):
            raise InvalidInput('SAM 3 retornou uma resposta incompleta para os prompts.')
        return predictions
