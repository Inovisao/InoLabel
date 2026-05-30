import json
import os
import tempfile
import unittest
from pathlib import Path

from app.core.output_state import (
    create_new_output_dir,
    find_annotations_path,
    latest_output_state_for_sources,
    list_output_states_for_sources,
    latest_output_state,
    list_output_states,
    load_annotation_state,
    output_dir_from_annotations_path,
)
from app.core.session import AnnotationTaskMode


class OutputStateTest(unittest.TestCase):
    def _write_annotations(
        self,
        root: Path,
        *,
        mode="tracking",
        categories=None,
        images=None,
        annotations=None,
        sources=None,
        data_root=None,
        use_saved_states_subdir=False,
    ):
        info = {"task_mode": mode}
        if sources is not None:
            info["video_sources"] = [str(source) for source in sources]
        if data_root is not None:
            info["data_root"] = str(data_root)
        payload = {
            "info": info,
            "categories": categories or [{"id": 2, "name": "car"}, {"id": 7, "name": "bus"}],
            "images": images or [{"id": 1, "file_name": "img.jpg"}],
            "annotations": annotations or [{"id": 1, "image_id": 1, "category_id": 2}],
        }
        if use_saved_states_subdir:
            ann_dir = root / "saved_data_states"
        else:
            ann_dir = root
        ann_dir.mkdir(parents=True, exist_ok=True)
        path = ann_dir / "annotations.coco.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_create_new_output_dir_creates_session_and_subdirs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = Path(tmp_dir)
            result = create_new_output_dir(outputs, "my_project")

            self.assertEqual(result.name, "my_project")
            self.assertTrue((result / "images").exists())
            self.assertTrue((result / "saved_data_states").exists())

    def test_create_new_output_dir_can_skip_images_subfolder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = Path(tmp_dir)
            result = create_new_output_dir(outputs, "my_project", create_images_dir=False)

            self.assertEqual(result.name, "my_project")
            self.assertFalse((result / "images").exists())
            self.assertTrue((result / "saved_data_states").exists())

    def test_create_new_output_dir_avoids_name_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = Path(tmp_dir)
            first = create_new_output_dir(outputs, "campo")
            second = create_new_output_dir(outputs, "campo")

            self.assertEqual(first.name, "campo")
            self.assertEqual(second.name, "campo_001")

    def test_create_new_output_dir_raises_on_empty_name(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                create_new_output_dir(Path(tmp_dir), "")

    def test_find_annotations_path_prefers_saved_data_states(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "project"
            # Write both legacy and new-style paths
            root.mkdir()
            (root / "annotations.coco.json").write_text("{}", encoding="utf-8")
            (root / "saved_data_states").mkdir()
            new_path = root / "saved_data_states" / "annotations.coco.json"
            new_path.write_text("{}", encoding="utf-8")

            found = find_annotations_path(root)
            self.assertEqual(found, new_path)

    def test_find_annotations_path_falls_back_to_root_for_legacy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "project"
            root.mkdir()
            legacy = root / "annotations.coco.json"
            legacy.write_text("{}", encoding="utf-8")

            found = find_annotations_path(root)
            self.assertEqual(found, legacy)

    def test_output_dir_from_annotations_path_new_layout(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            (project / "saved_data_states").mkdir(parents=True)
            ann = project / "saved_data_states" / "annotations.coco.json"
            ann.write_text("{}", encoding="utf-8")

            self.assertEqual(output_dir_from_annotations_path(ann), project)

    def test_output_dir_from_annotations_path_legacy_layout(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            project.mkdir()
            ann = project / "annotations.coco.json"
            ann.write_text("{}", encoding="utf-8")

            self.assertEqual(output_dir_from_annotations_path(ann), project)

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

    def test_lists_output_states_new_layout(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = Path(tmp_dir)
            project = outputs / "my_project"
            project.mkdir()
            self._write_annotations(project, categories=[{"id": 1, "name": "cat"}], use_saved_states_subdir=True)

            states = list_output_states(outputs)
            self.assertEqual(len(states), 1)
            self.assertEqual(states[0].path.name, "my_project")
            self.assertEqual(states[0].class_names, ("cat",))

    def test_latest_output_state_uses_annotation_file_mtime(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = Path(tmp_dir)
            older_name = outputs / "output_dataset99_20260427_120000"
            newer_name = outputs / "output_dataset1_20260427_100000"
            older_path = self._write_annotations(older_name, categories=[{"id": 1, "name": "old"}])
            newer_path = self._write_annotations(newer_name, categories=[{"id": 1, "name": "new"}])
            os.utime(older_path, (1_779_980_400, 1_779_980_400))
            os.utime(newer_path, (1_779_984_000, 1_779_984_000))

            states = list_output_states(outputs)
            latest = latest_output_state(outputs)

        self.assertEqual([state.path.name for state in states], [older_name.name, newer_name.name])
        self.assertEqual(latest.path.name, newer_name.name)
        self.assertEqual(latest.class_names, ("new",))

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

    def test_supports_obb_annotations_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "output_dataset1_20260427_100000"
            root.mkdir(parents=True)
            path = root / "annotations_obb.coco.json"
            path.write_text(
                json.dumps(
                    {
                        "info": {"task_mode": "obb"},
                        "categories": [{"id": 1, "name": "seed"}],
                        "images": [],
                        "annotations": [],
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_annotation_state(root)

        self.assertEqual(loaded.annotations_path.name, "annotations_obb.coco.json")
        self.assertEqual(loaded.task_mode, AnnotationTaskMode.OBB)
        self.assertEqual(loaded.class_names, ("seed",))

    def test_filters_output_states_by_project_sources(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project_a = root / "project_a"
            project_b = root / "project_b"
            project_a.mkdir()
            project_b.mkdir()
            outputs = root / "outputs"
            old_for_a = outputs / "output_dataset1_20260427_100000"
            newer_for_b = outputs / "output_dataset2_20260427_110000"
            self._write_annotations(old_for_a, categories=[{"id": 1, "name": "a"}], sources=[project_a])
            self._write_annotations(newer_for_b, categories=[{"id": 1, "name": "b"}], sources=[project_b])

            states = list_output_states_for_sources([project_a], outputs)
            latest = latest_output_state_for_sources([project_a], outputs)

        self.assertEqual([state.path.name for state in states], [old_for_a.name])
        self.assertEqual(latest.path.name, old_for_a.name)
        self.assertEqual(latest.class_names, ("a",))


if __name__ == "__main__":
    unittest.main()
