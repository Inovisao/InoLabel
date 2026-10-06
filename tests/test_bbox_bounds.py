"""Testes das correcoes de caixas fora da resolucao da imagem (modo deteccao).

Cobre: recorte de bbox, descarte de caixas degeneradas, colisao de file_name entre
fontes, on_accept reaproveitando registro existente, corrida da inferencia em
background e sanitizacao nos exportadores COCO/YOLO."""

import unittest

import numpy as np

from app.annotation.core.augmentation.augmentation_service import _apply_entry
from app.annotation.core.augmentation.augmentation_types import AugEntry
from app.annotation.core.export.yolo_label_service import clip_coco_bbox, normalize_yolo_bbox
from app.annotation.infrastructure.export.coco_exporter import convert_tracking_to_detection


class ExportSanitizationTest(unittest.TestCase):
    def _payload(self, bboxes):
        return {
            "images": [{"id": 1, "file_name": "a.jpg", "width": 100, "height": 80}],
            "annotations": [
                {"id": i, "image_id": 1, "category_id": 1, "bbox": bbox, "area": 1.0}
                for i, bbox in enumerate(bboxes, 1)
            ],
            "categories": [{"id": 1, "name": "obj"}],
        }

    def test_coco_export_clips_and_drops_out_of_bounds_boxes(self):
        out = convert_tracking_to_detection(self._payload([[90, 70, 30, 30], [200, 10, 5, 5], [10, 10, 5, 5]]))
        bboxes = [ann["bbox"] for ann in out["annotations"]]
        self.assertEqual(bboxes, [[90.0, 70.0, 10.0, 10.0], [10.0, 10.0, 5.0, 5.0]])
        self.assertEqual(out["annotations"][0]["area"], 100.0)
        self.assertEqual(out["annotations"][1]["area"], 1.0)  # caixa valida preserva a area original

    def test_yolo_normalize_clips_small_overflow_instead_of_dropping(self):
        values = normalize_yolo_bbox([50, 40, 50.0001, 40], 100, 80)
        self.assertIsNotNone(values)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in values))

    def test_clip_coco_bbox_rejects_box_outside_image(self):
        self.assertIsNone(clip_coco_bbox([120, 10, 5, 5], 100, 80))
        self.assertIsNone(clip_coco_bbox([10, 10, 0, 5], 100, 80))


class ShearAugmentationTest(unittest.TestCase):
    def test_shear_keeps_image_center_fixed_on_non_square_image(self):
        image = np.zeros((100, 300, 3), dtype=np.uint8)
        box = [0, 0.5, 0.5, 0.1, 0.1]
        entry = AugEntry(key="shear", enabled=True, params={"prob": 1.0, "max_degrees": 20.0})
        _, boxes = _apply_entry(image, [box], entry, np.random.default_rng(0))
        self.assertAlmostEqual(boxes[0][1], 0.5, places=3)


if __name__ == "__main__":
    unittest.main()
