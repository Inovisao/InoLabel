import tempfile
import unittest
from pathlib import Path

import numpy as np

from app.annotation.detection.persistence import PersistenceMixin
from app.annotation.detection.workflow_actions import WorkflowActionsMixin
from app.config import DATA_ROOT
from app.dataset_export import export_yolo_dataset
from utils.merge_yolo_splits import merge_yolo_splits


class ExportYoloDatasetTest(unittest.TestCase):
    def test_keeps_empty_image_in_train_without_special_split_handling(self):
        payload = {
            "images": [
                {"id": 1, "file_name": "img_001.jpg", "width": 100, "height": 100},
                {"id": 2, "file_name": "img_002.jpg", "width": 100, "height": 100},
                {"id": 3, "file_name": "img_003.jpg", "width": 100, "height": 100},
                {"id": 4, "file_name": "img_004.jpg", "width": 100, "height": 100},
                {"id": 5, "file_name": "img_005.jpg", "width": 100, "height": 100},
                {"id": 6, "file_name": "img_006.jpg", "width": 100, "height": 100},
            ],
            "annotations": [
                {"id": 1, "image_id": 2, "category_id": 1, "bbox": [10, 10, 20, 20]},
                {"id": 2, "image_id": 3, "category_id": 1, "bbox": [15, 15, 20, 20]},
                {"id": 3, "image_id": 5, "category_id": 1, "bbox": [20, 20, 20, 20]},
            ],
            "categories": [{"id": 1, "name": "car"}],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_images_dir = tmp_path / "images"
            dataset_root = tmp_path / "yolo_dataset"
            source_images_dir.mkdir(parents=True, exist_ok=True)

            for image in payload["images"]:
                (source_images_dir / image["file_name"]).write_bytes(b"fake-image")

            report = export_yolo_dataset(
                payload,
                source_images_dir=source_images_dir,
                dataset_root=dataset_root,
                split_ratios=(0.5, 0.25, 0.25),
            )

            self.assertEqual(report["images_per_split"], {"train": 3, "val": 2, "test": 1})
            self.assertEqual(report["empty_images_per_split"], {"train": 1, "val": 1, "test": 1})
            self.assertEqual(
                (dataset_root / "labels" / "train" / "img_001.txt").read_text(encoding="utf-8"),
                "",
            )
            self.assertTrue((dataset_root / "images" / "train" / "img_001.jpg").exists())

    def test_preserves_subfolders_for_images_and_labels(self):
        payload = {
            "images": [
                {"id": 1, "file_name": "lote_a/img_001.jpg", "width": 100, "height": 100},
                {"id": 2, "file_name": "lote_b/img_002.jpg", "width": 100, "height": 100},
            ],
            "annotations": [
                {"id": 1, "image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20]},
            ],
            "categories": [{"id": 1, "name": "car"}],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_images_dir = tmp_path / "images"
            dataset_root = tmp_path / "yolo_dataset"
            for image in payload["images"]:
                image_path = source_images_dir / image["file_name"]
                image_path.parent.mkdir(parents=True, exist_ok=True)
                image_path.write_bytes(b"fake-image")

            export_yolo_dataset(
                payload,
                source_images_dir=source_images_dir,
                dataset_root=dataset_root,
                split_ratios=(1.0, 0.0, 0.0),
            )

            self.assertTrue((dataset_root / "images" / "train" / "lote_a" / "img_001.jpg").exists())
            self.assertTrue((dataset_root / "labels" / "train" / "lote_a" / "img_001.txt").exists())
            self.assertTrue((dataset_root / "images" / "train" / "lote_b" / "img_002.jpg").exists())
            self.assertTrue((dataset_root / "labels" / "train" / "lote_b" / "img_002.txt").exists())


class PersistenceMixinTest(unittest.TestCase):
    def test_build_output_file_name_uses_relative_path_inside_data_root(self):
        class DummyPersistence(PersistenceMixin):
            pass

        persistence = DummyPersistence()
        persistence.data_root = DATA_ROOT
        persistence.current_source_type = "images"
        persistence.current_source_image_path = DATA_ROOT / "lote_a" / "img_001.jpg"
        persistence.video_path = DATA_ROOT
        persistence.video_name = DATA_ROOT.name

        self.assertEqual(
            persistence.build_output_file_name(new_frame=True, existing_file_name=None),
            "lote_a/img_001.jpg",
        )


class WorkflowActionsTest(unittest.TestCase):
    def test_accept_saves_empty_frame(self):
        class DummyWorkflow(WorkflowActionsMixin):
            def __init__(self):
                self.current_frame = np.zeros((16, 16, 3), dtype=np.uint8)
                self.current_detections = []
                self.manual_detections = []
                self.review_idx = None
                self.saved_records = []
                self.store_calls = []
                self.write_calls = 0
                self.load_next_frame_calls = 0

            def store_annotations(self, detections, existing_image_id=None, existing_file_name=None):
                self.store_calls.append(
                    {
                        "detections": list(detections),
                        "existing_image_id": existing_image_id,
                        "existing_file_name": existing_file_name,
                    }
                )
                return 7, "frame_00007.jpg"

            def write_annotations(self):
                self.write_calls += 1

            def append_saved_record(self, detections, image_id, file_name):
                self.saved_records.append(
                    {"detections": list(detections), "image_id": image_id, "file_name": file_name}
                )

            def load_next_frame(self):
                self.load_next_frame_calls += 1

            def update_manual_memory_after_accept(self, detections):
                raise AssertionError("Nao deveria atualizar memoria manual sem deteccoes.")

        workflow = DummyWorkflow()

        workflow.on_accept()

        self.assertEqual(len(workflow.store_calls), 1)
        self.assertEqual(workflow.store_calls[0]["detections"], [])
        self.assertEqual(workflow.write_calls, 1)
        self.assertEqual(len(workflow.saved_records), 1)
        self.assertEqual(workflow.saved_records[0]["detections"], [])
        self.assertEqual(workflow.load_next_frame_calls, 1)


class MergeYoloSplitsTest(unittest.TestCase):
    def test_merges_all_splits_into_train_only_dataset(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_root = tmp_path / "yolo_dataset"
            output_root = tmp_path / "yolo_dataset_train_only"

            for split in ("train", "val", "test"):
                (input_root / "images" / split).mkdir(parents=True, exist_ok=True)
                (input_root / "labels" / split).mkdir(parents=True, exist_ok=True)

            (input_root / "images" / "train" / "img_train.jpg").write_bytes(b"train-image")
            (input_root / "labels" / "train" / "img_train.txt").write_text(
                "0 0.500000 0.500000 0.200000 0.200000\n",
                encoding="utf-8",
            )
            (input_root / "images" / "val" / "img_val.jpg").write_bytes(b"val-image")
            (input_root / "labels" / "val" / "img_val.txt").write_text("", encoding="utf-8")
            (input_root / "images" / "test" / "img_test.jpg").write_bytes(b"test-image")
            (input_root / "labels" / "test" / "img_test.txt").write_text("", encoding="utf-8")
            (input_root / "data.yaml").write_text(
                "\n".join(
                    [
                        f"path: {input_root}",
                        "train: images/train",
                        "val: images/val",
                        "test: images/test",
                        "",
                        "names:",
                        "  0: car",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = merge_yolo_splits(input_root, output_root)

            self.assertEqual(report["merged_counts"], {"train": 1, "val": 1, "test": 1})
            self.assertEqual(report["total_images"], 3)
            self.assertEqual(report["empty_label_files"], 2)
            self.assertTrue((output_root / "images" / "train" / "img_train.jpg").exists())
            self.assertTrue((output_root / "images" / "train" / "img_val.jpg").exists())
            self.assertTrue((output_root / "images" / "train" / "img_test.jpg").exists())
            self.assertEqual(
                (output_root / "labels" / "train" / "img_val.txt").read_text(encoding="utf-8"),
                "",
            )
            output_yaml = (output_root / "data.yaml").read_text(encoding="utf-8")
            self.assertIn("train: images/train", output_yaml)
            self.assertNotIn("val: images/val", output_yaml)
            self.assertNotIn("test: images/test", output_yaml)


if __name__ == "__main__":
    unittest.main()
