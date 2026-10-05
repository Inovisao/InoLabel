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

    def test_new_folder_inside_old_dataset_does_not_resume_old_project(self):
        """Regressao: escolher datasets/lote_novo retomava o projeto cujo dataset era datasets/."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            parent = root / "datasets"
            new_folder = parent / "lote_novo"
            new_folder.mkdir(parents=True)
            outputs = root / "outputs"
            old_project = outputs / "projeto_antigo"
            self._write_annotations(old_project, sources=[parent], data_root=parent)

            self.assertEqual(list_output_states_for_sources([new_folder], outputs), [])
            self.assertIsNone(latest_output_state_for_sources([new_folder], outputs))
            # O proprio dataset do projeto continua sendo reconhecido.
            self.assertEqual(
                [s.path.name for s in list_output_states_for_sources([parent], outputs)], ["projeto_antigo"]
            )

    def test_parent_folder_does_not_resume_project_of_a_subfolder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            parent = root / "datasets"
            child = parent / "lote_a"
            child.mkdir(parents=True)
            outputs = root / "outputs"
            self._write_annotations(outputs / "projeto_lote_a", sources=[child], data_root=child)

            self.assertEqual(list_output_states_for_sources([parent], outputs), [])

    def test_video_listed_in_state_still_matches(self):
        """Selecionar um video que o projeto ja usava continua retomando o projeto."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            folder = root / "videos"
            folder.mkdir()
            video = folder / "cam1.mp4"
            video.write_bytes(b"")
            outputs = root / "outputs"
            self._write_annotations(outputs / "projeto", sources=[video], data_root=folder)

            self.assertEqual([s.path.name for s in list_output_states_for_sources([video], outputs)], ["projeto"])


class ClassificationStateMatchingTest(unittest.TestCase):
    def test_new_folder_inside_old_source_does_not_resume(self):
        from app.classification.dataset import list_output_states_for_sources as list_cls_states, write_state

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            parent = root / "fotos"
            new_folder = parent / "lote_novo"
            new_folder.mkdir(parents=True)
            outputs = root / "outputs"
            project = outputs / "projeto_antigo"
            project.mkdir(parents=True)
            from app.classification.dataset import STATE_FILE_NAME
            write_state(project / STATE_FILE_NAME, classes=["a"], class_directories={},
                        source_root=parent, records=[])

            self.assertEqual(list_cls_states([new_folder], outputs), [])
            self.assertEqual([s.path.name for s in list_cls_states([parent], outputs)], ["projeto_antigo"])


if __name__ == "__main__":
    unittest.main()
