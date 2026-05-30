"""Tests for the session setup flow (wizard "installer").

These tests verify that every step of initialising, resuming, and discovering
annotation sessions works correctly after the output-structure refactor:

  <parent_dir>/<session_name>/
  ├── images/
  └── saved_data_states/
      ├── annotations.coco.json
      └── homography.json
"""

import json
import tempfile
import unittest
from pathlib import Path

from app.core.output_state import (
    ANNOTATION_FILE_NAMES,
    create_new_output_dir,
    find_annotations_path,
    latest_output_state,
    latest_output_state_for_sources,
    list_output_states,
    list_output_states_for_sources,
    load_annotation_state,
    output_dir_from_annotations_path,
)
from app.core.session import AnnotationSessionConfig, AnnotationTaskMode
from app.core.startup_cache import load_startup_cache, save_startup_cache


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_session(parent: Path, name: str, *, mode="detection", categories=None, sources=None) -> Path:
    """Create a fully-populated session directory (new layout)."""
    session_dir = create_new_output_dir(parent, name)
    ann_dir = session_dir / "saved_data_states"
    info: dict = {"task_mode": mode}
    if sources:
        info["video_sources"] = [str(s) for s in sources]
    payload = {
        "info": info,
        "categories": categories or [{"id": 1, "name": "car"}],
        "images": [{"id": 1, "file_name": "img.jpg", "width": 100, "height": 100}],
        "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 10, 10]}],
    }
    (ann_dir / "annotations.coco.json").write_text(json.dumps(payload), encoding="utf-8")
    return session_dir


def _make_legacy_session(parent: Path, name: str, *, mode="detection", categories=None) -> Path:
    """Create a session using the old layout (annotations at root, no saved_data_states/)."""
    session_dir = parent / name
    session_dir.mkdir(parents=True)
    (session_dir / "images").mkdir()
    info = {"task_mode": mode}
    payload = {
        "info": info,
        "categories": categories or [{"id": 1, "name": "car"}],
        "images": [],
        "annotations": [],
    }
    (session_dir / "annotations.coco.json").write_text(json.dumps(payload), encoding="utf-8")
    return session_dir


# ── create_new_output_dir ──────────────────────────────────────────────────────

class CreateNewOutputDirTest(unittest.TestCase):

    def test_creates_session_with_expected_subdirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = create_new_output_dir(Path(tmp), "campo_2025")
            self.assertTrue(result.is_dir())
            self.assertTrue((result / "images").is_dir())
            self.assertTrue((result / "saved_data_states").is_dir())

    def test_session_name_used_as_folder_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = create_new_output_dir(Path(tmp), "meu_projeto")
            self.assertEqual(result.name, "meu_projeto")

    def test_collision_gets_numeric_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = create_new_output_dir(Path(tmp), "projeto")
            second = create_new_output_dir(Path(tmp), "projeto")
            third = create_new_output_dir(Path(tmp), "projeto")
            self.assertEqual(first.name, "projeto")
            self.assertEqual(second.name, "projeto_001")
            self.assertEqual(third.name, "projeto_002")

    def test_empty_name_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                create_new_output_dir(Path(tmp), "")
            with self.assertRaises(ValueError):
                create_new_output_dir(Path(tmp), "   ")

    def test_skip_images_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = create_new_output_dir(Path(tmp), "classify", create_images_dir=False)
            self.assertFalse((result / "images").exists())
            self.assertTrue((result / "saved_data_states").is_dir())

    def test_creates_parent_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            deep = Path(tmp) / "a" / "b" / "c"
            result = create_new_output_dir(deep, "session")
            self.assertTrue(result.is_dir())


# ── find_annotations_path ─────────────────────────────────────────────────────

class FindAnnotationsPathTest(unittest.TestCase):

    def test_finds_file_in_saved_data_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            sds = Path(tmp) / "saved_data_states"
            sds.mkdir()
            ann = sds / "annotations.coco.json"
            ann.write_text("{}", encoding="utf-8")
            self.assertEqual(find_annotations_path(Path(tmp)), ann)

    def test_falls_back_to_root_for_legacy_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            ann = Path(tmp) / "annotations.coco.json"
            ann.write_text("{}", encoding="utf-8")
            self.assertEqual(find_annotations_path(Path(tmp)), ann)

    def test_prefers_saved_data_states_over_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Both locations exist — saved_data_states/ should win
            (root / "annotations.coco.json").write_text("{}", encoding="utf-8")
            sds = root / "saved_data_states"
            sds.mkdir()
            new = sds / "annotations.coco.json"
            new.write_text("{}", encoding="utf-8")
            self.assertEqual(find_annotations_path(root), new)

    def test_returns_none_when_no_annotations_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_annotations_path(Path(tmp)))

    def test_direct_file_path_returned_as_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            ann = Path(tmp) / "__annotations.coco.json"
            ann.write_text("{}", encoding="utf-8")
            self.assertEqual(find_annotations_path(ann), ann)

    def test_finds_obb_annotations_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            sds = Path(tmp) / "saved_data_states"
            sds.mkdir()
            ann = sds / "annotations_obb.coco.json"
            ann.write_text("{}", encoding="utf-8")
            found = find_annotations_path(Path(tmp))
            self.assertEqual(found, ann)


# ── output_dir_from_annotations_path ─────────────────────────────────────────

class OutputDirFromAnnotationsPathTest(unittest.TestCase):

    def test_new_layout_returns_project_root(self):
        path = Path("/projects/my_project/saved_data_states/annotations.coco.json")
        self.assertEqual(output_dir_from_annotations_path(path), Path("/projects/my_project"))

    def test_legacy_layout_returns_annotations_parent(self):
        path = Path("/projects/my_project/annotations.coco.json")
        self.assertEqual(output_dir_from_annotations_path(path), Path("/projects/my_project"))

    def test_obb_annotations_file_new_layout(self):
        path = Path("/projects/proj/saved_data_states/annotations_obb.coco.json")
        self.assertEqual(output_dir_from_annotations_path(path), Path("/projects/proj"))


# ── load_annotation_state ─────────────────────────────────────────────────────

class LoadAnnotationStateTest(unittest.TestCase):

    def test_loads_from_saved_data_states_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = _make_session(Path(tmp), "proj", mode="tracking",
                                    categories=[{"id": 1, "name": "doc"}])
            loaded = load_annotation_state(session)
            self.assertEqual(loaded.task_mode, AnnotationTaskMode.TRACKING)
            self.assertEqual(loaded.class_names, ("doc",))
            self.assertEqual(loaded.output_dir, session)

    def test_loads_from_legacy_root_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = _make_legacy_session(Path(tmp), "old_proj", mode="detection",
                                           categories=[{"id": 1, "name": "plate"}])
            loaded = load_annotation_state(session)
            self.assertEqual(loaded.task_mode, AnnotationTaskMode.DETECTION)
            self.assertEqual(loaded.class_names, ("plate",))
            self.assertEqual(loaded.output_dir, session)

    def test_output_dir_is_project_root_not_saved_states_subdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = _make_session(Path(tmp), "proj")
            loaded = load_annotation_state(session)
            # Must return the project root, not saved_data_states/
            self.assertNotIn("saved_data_states", str(loaded.output_dir))
            self.assertEqual(loaded.output_dir, session)

    def test_raises_when_no_annotations_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty_project"
            empty.mkdir()
            with self.assertRaises(FileNotFoundError):
                load_annotation_state(empty)


# ── list / latest output states ───────────────────────────────────────────────

class ListOutputStatesTest(unittest.TestCase):

    def test_lists_new_layout_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            _make_session(parent, "alpha")
            _make_session(parent, "beta")
            states = list_output_states(parent)
            names = {s.path.name for s in states}
            self.assertIn("alpha", names)
            self.assertIn("beta", names)

    def test_lists_legacy_layout_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            _make_legacy_session(parent, "legacy_project")
            states = list_output_states(parent)
            self.assertEqual(len(states), 1)
            self.assertEqual(states[0].path.name, "legacy_project")

    def test_lists_mixed_new_and_legacy_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            _make_session(parent, "new_session")
            _make_legacy_session(parent, "old_session")
            states = list_output_states(parent)
            self.assertEqual(len(states), 2)

    def test_ignores_dirs_without_annotations(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            (parent / "random_dir").mkdir()
            _make_session(parent, "valid_session")
            states = list_output_states(parent)
            self.assertEqual(len(states), 1)

    def test_returns_empty_list_for_missing_parent(self):
        states = list_output_states(Path("/nonexistent/path/xyz"))
        self.assertEqual(states, [])

    def test_filters_by_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            src_a = parent / "dataset_a"
            src_b = parent / "dataset_b"
            src_a.mkdir()
            src_b.mkdir()
            _make_session(parent, "session_a", sources=[src_a])
            _make_session(parent, "session_b", sources=[src_b])

            states_a = list_output_states_for_sources([src_a], parent)
            self.assertEqual(len(states_a), 1)
            self.assertEqual(states_a[0].path.name, "session_a")

    def test_latest_returns_most_recently_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            _make_session(parent, "first")
            latest_session = _make_session(parent, "second")
            latest = latest_output_state(parent)
            self.assertEqual(latest.path, latest_session)

    def test_latest_for_sources_returns_correct_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            src = parent / "dataset"
            src.mkdir()
            _make_session(parent, "session_for_src", sources=[src])
            _make_session(parent, "unrelated_session")
            latest = latest_output_state_for_sources([src], parent)
            self.assertIsNotNone(latest)
            self.assertEqual(latest.path.name, "session_for_src")


# ── startup cache with parent_dir ─────────────────────────────────────────────

class StartupCacheParentDirTest(unittest.TestCase):

    def test_saves_and_loads_parent_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            parent = Path(tmp) / "my_projects"
            parent.mkdir()
            save_startup_cache(
                data_root=Path(tmp) / "dataset",
                mode=AnnotationTaskMode.DETECTION,
                parent_dir=parent,
                path=cache_path,
            )
            loaded = load_startup_cache(cache_path)
            self.assertEqual(loaded.parent_dir, parent)

    def test_parent_dir_is_none_when_not_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            save_startup_cache(
                data_root=Path(tmp) / "dataset",
                mode=AnnotationTaskMode.DETECTION,
                path=cache_path,
            )
            loaded = load_startup_cache(cache_path)
            self.assertIsNone(loaded.parent_dir)

    def test_old_cache_without_parent_dir_loads_without_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            # Write cache in old format (no parent_dir key)
            cache_path.write_text(
                '{"data_root": "/tmp/data", "weights_paths": [], "mode": "detection"}\n',
                encoding="utf-8",
            )
            loaded = load_startup_cache(cache_path)
            self.assertIsNone(loaded.parent_dir)
            self.assertEqual(loaded.mode, AnnotationTaskMode.DETECTION)


# ── session config path derivation ────────────────────────────────────────────

class SessionConfigPathTest(unittest.TestCase):

    def test_config_output_dir_is_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "my_project"
            output_dir.mkdir()
            config = AnnotationSessionConfig(
                mode=AnnotationTaskMode.DETECTION,
                data_root=Path(tmp),
                target_classes=("car",),
                output_dir=output_dir,
            )
            self.assertEqual(config.output_dir, output_dir)

    def test_config_with_saved_states_annotations_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            sds = project / "saved_data_states"
            sds.mkdir(parents=True)
            ann = sds / "annotations.coco.json"
            ann.write_text("{}", encoding="utf-8")
            config = AnnotationSessionConfig(
                mode=AnnotationTaskMode.TRACKING,
                data_root=Path(tmp),
                target_classes=("person",),
                output_dir=project,
                annotations_path=ann,
                resume_existing_annotations=True,
            )
            self.assertEqual(config.annotations_path, ann)
            self.assertTrue(config.resume_existing_annotations)

    def test_resume_flag_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = AnnotationSessionConfig(
                mode=AnnotationTaskMode.DETECTION,
                data_root=Path(tmp),
                target_classes=("a",),
                output_dir=Path(tmp) / "proj",
                resume_existing_annotations=True,
            )
            self.assertTrue(config.resume_existing_annotations)


if __name__ == "__main__":
    unittest.main()
