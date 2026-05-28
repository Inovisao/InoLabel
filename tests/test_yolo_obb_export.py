import json
import tempfile
import unittest
from pathlib import Path

from backend.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset


class YOLOOBBExportTest(unittest.TestCase):
    def test_exports_normalized_xyxyxyxy_labels(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source_images = root / "images"
            source_images.mkdir()
            (source_images / "img.jpg").write_bytes(b"fake")
            payload = {
                "categories": [{"id": 2, "name": "doc"}],
                "images": [{"id": 1, "file_name": "img.jpg", "width": 100, "height": 50}],
                "annotations": [
                    {
                        "id": 1,
                        "image_id": 1,
                        "category_id": 2,
                        "obb": {"cx": 50, "cy": 25, "width": 40, "height": 10, "angle": 0},
                    }
                ],
            }

            summary = export_yolo_obb_dataset(payload, root / "out", source_images)
            label = (root / "out" / "labels" / "train" / "img.txt").read_text(encoding="utf-8").strip()

        self.assertEqual(summary["images"], 1)
        self.assertEqual(summary["labels"], 1)
        self.assertEqual(label, "0 0.300000 0.400000 0.700000 0.400000 0.700000 0.600000 0.300000 0.600000")


if __name__ == "__main__":
    unittest.main()
