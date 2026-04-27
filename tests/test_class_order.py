import tempfile
import unittest
from pathlib import Path

from app.dataset_export import export_yolo_dataset


class ClassOrderExportTest(unittest.TestCase):
    def test_yolo_export_uses_category_sequence_as_class_index(self):
        payload = {
            "images": [{"id": 1, "file_name": "img_001.jpg", "width": 100, "height": 100}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 2, "bbox": [10, 10, 20, 20]}],
            "categories": [
                {"id": 5, "name": "bus"},
                {"id": 2, "name": "car"},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_images_dir = tmp_path / "images"
            dataset_root = tmp_path / "yolo_dataset"
            source_images_dir.mkdir(parents=True, exist_ok=True)
            (source_images_dir / "img_001.jpg").write_bytes(b"fake-image")

            export_yolo_dataset(
                payload,
                source_images_dir=source_images_dir,
                dataset_root=dataset_root,
                split_ratios=(1.0, 0.0, 0.0),
            )

            data_yaml = (dataset_root / "data.yaml").read_text(encoding="utf-8")
            label = (dataset_root / "labels" / "train" / "img_001.txt").read_text(encoding="utf-8")

        self.assertIn("  0: bus", data_yaml)
        self.assertIn("  1: car", data_yaml)
        self.assertTrue(label.startswith("1 "))


if __name__ == "__main__":
    unittest.main()
