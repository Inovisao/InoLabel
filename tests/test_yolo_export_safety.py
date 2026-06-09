import tempfile
import unittest
from pathlib import Path

from app.annotation.infrastructure.export.yolo_exporter import export_yolo_no_split


class YoloExportSafetyTest(unittest.TestCase):
    def test_rejects_path_traversal_in_filenames(self):
        payload = {
            "images": [{"id": 1, "file_name": "../evil.jpg", "width": 10, "height": 10}],
            "annotations": [],
            "categories": [{"id": 1, "name": "car"}],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_images_dir = tmp_path / "images"
            source_images_dir.mkdir(parents=True)
            # create the file outside the source_images_dir to simulate potential traversal
            evil_path = tmp_path.parent / "evil.jpg"
            evil_path.write_bytes(b"fake")

            with self.assertRaises(ValueError):
                export_yolo_no_split(payload, source_images_dir=source_images_dir, dataset_root=tmp_path / "out")

    def test_preserves_subfolders_for_no_split_export(self):
        payload = {
            "images": [
                {"id": 1, "file_name": "lote_a/img_001.jpg", "width": 100, "height": 100},
            ],
            "annotations": [],
            "categories": [{"id": 1, "name": "car"}],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_images_dir = tmp_path / "images"
            dataset_root = tmp_path / "yolo_dataset"
            image_path = source_images_dir / "lote_a" / "img_001.jpg"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(b"fake-image")

            report = export_yolo_no_split(payload, source_images_dir=source_images_dir, dataset_root=dataset_root)

            self.assertTrue((dataset_root / "images" / "all" / "lote_a" / "img_001.jpg").exists())
            self.assertTrue((dataset_root / "labels" / "all" / "lote_a" / "img_001.txt").exists())


if __name__ == "__main__":
    unittest.main()
