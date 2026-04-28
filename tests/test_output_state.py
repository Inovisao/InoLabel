import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.core.output_state import (
    create_new_output_dir,
    latest_output_state,
    list_output_states,
    load_annotation_state,
)
from app.core.session import AnnotationTaskMode


class OutputStateTest(unittest.TestCase):
    def _write_annotations(self, root: Path, *, mode="tracking", categories=None, images=None, annotations=None):
        payload = {
            "info": {"task_mode": mode},
            "categories": categories or [{"id": 2, "name": "car"}, {"id": 7, "name": "bus"}],
            "images": images or [{"id": 1, "file_name": "img.jpg"}],
            "annotations": annotations or [{"id": 1, "image_id": 1, "category_id": 2}],
        }
        root.mkdir(parents=True, exist_ok=True)
        path = root / "annotations.coco.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_create_new_output_dir_uses_incrementing_index_and_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = Path(tmp_dir)
            first = create_new_output_dir(outputs, now=datetime(2026, 4, 27, 10, 0, 0))
            self._write_annotations(first)
            second = create_new_output_dir(outputs, now=datetime(2026, 4, 27, 11, 0, 0))

            self.assertEqual(first.name, "output_dataset1_20260427_100000")
            self.assertEqual(second.name, "output_dataset2_20260427_110000")
            self.assertTrue((second / "images").exists())

    def test_lists_and_loads_output_states_from_annotations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = Path(tmp_dir)
            old = outputs / "output_dataset1_20260427_100000"
            new = outputs / "output_dataset2_20260427_110000"
            self._write_annotations(old, categories=[{"id": 5, "name": "doc"}])
            self._write_annotations(new, mode="detection", categories=[{"id": 9, "name": "plate"}])

            states = list_output_states(outputs)
            latest = latest_output_state(outputs)
            loaded = load_annotation_state(new)

        self.assertEqual([state.path.name for state in states], [old.name, new.name])
        self.assertEqual(latest.path.name, new.name)
        self.assertEqual(loaded.task_mode, AnnotationTaskMode.DETECTION)
        self.assertEqual(loaded.class_names, ("plate",))
        self.assertEqual(loaded.image_count, 1)
        self.assertEqual(loaded.annotation_count, 1)

    def test_supports_double_underscore_annotations_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "output_dataset1_20260427_100000"
            root.mkdir(parents=True)
            path = root / "__annotations.coco.json"
            path.write_text(
                json.dumps({"categories": [{"id": 1, "name": "person"}], "images": [], "annotations": []}),
                encoding="utf-8",
            )

            loaded = load_annotation_state(root)

        self.assertEqual(loaded.annotations_path.name, "__annotations.coco.json")
        self.assertEqual(loaded.class_names, ("person",))


if __name__ == "__main__":
    unittest.main()
