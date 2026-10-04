"""Protecoes de dados para a 2.0: exportacao nunca apaga pastas do usuario (C1) e
estado ilegivel nunca e sobrescrito (C2)."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import cv2
import numpy as np

from app.annotation.infrastructure.export.export_dir import (
    EXPORT_MARKER,
    UnsafeExportDirError,
    ensure_export_dir,
    is_inolabel_export,
    reset_export_dir,
)
from app.annotation.infrastructure.export.yolo_exporter import export_yolo_dataset
from app.annotation.infrastructure.persistence.export_actions import ExportActionsMixin
from app.annotation.infrastructure.persistence.state_file import (
    AnnotationStateUnreadableError,
    read_annotation_state,
)
from app.annotation.sources.source_loading import SourceLoadingMixin
from app.annotation.state.core_init import CoreInitMixin
from app.annotation_keypoint.infrastructure.export.yolo_pose_exporter import export_yolo_pose_dataset
from app.annotation_keypoint.infrastructure.persistence.coco_storage import KPCocoStorageMixin
from app.annotation_obb.infrastructure.persistence.obb_coco_storage import OBBCocoStorageMixin


def _user_folder(path: Path) -> Path:
    """Pasta com um arquivo do usuario, que nenhuma exportacao pode apagar."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "importante.txt").write_text("nao apagar", encoding="utf-8")
    return path


# ── C1: guarda de pasta de exportacao ────────────────────────────────────────

class ExportDirGuardTest(unittest.TestCase):
    def test_reset_refuses_folder_not_created_by_inolabel(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _user_folder(Path(tmp) / "fotos")
            with self.assertRaises(UnsafeExportDirError):
                reset_export_dir(folder)
            self.assertTrue((folder / "importante.txt").exists())

    def test_reset_recreates_marked_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = reset_export_dir(Path(tmp) / "exp")
            (folder / "antigo.txt").write_text("x", encoding="utf-8")
            reset_export_dir(folder)
            self.assertFalse((folder / "antigo.txt").exists())
            self.assertTrue(is_inolabel_export(folder))

    def test_reset_accepts_empty_folder_and_marks_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "vazia"
            folder.mkdir()
            reset_export_dir(folder)
            self.assertTrue((folder / EXPORT_MARKER).is_file())

    def test_reset_refuses_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "arquivo"
            path.write_text("x", encoding="utf-8")
            with self.assertRaises(UnsafeExportDirError):
                reset_export_dir(path)

    def test_ensure_never_deletes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _user_folder(Path(tmp) / "fotos")
            with self.assertRaises(UnsafeExportDirError):
                ensure_export_dir(folder)
            self.assertTrue((folder / "importante.txt").exists())

    def test_yolo_exporters_refuse_unmarked_destination(self):
        payload = {"images": [], "annotations": [], "categories": [{"id": 1, "name": "a"}]}
        with tempfile.TemporaryDirectory() as tmp:
            folder = _user_folder(Path(tmp) / "meu_dataset")
            with self.assertRaises(UnsafeExportDirError):
                export_yolo_dataset(payload, Path(tmp), folder)
            with self.assertRaises(UnsafeExportDirError):
                export_yolo_pose_dataset(payload, folder, Path(tmp))
            self.assertTrue((folder / "importante.txt").exists())


class _Actions(ExportActionsMixin):
    def __init__(self, root: Path):
        self.output_dir = root / "state_saved" / "projeto" / "output_dataset_1"
        self.output_images_dir = self.output_dir / "images"
        self.output_images_dir.mkdir(parents=True)
        self.data_root = root / "dataset"
        self.data_root.mkdir()
        self.info_var = SimpleNamespace(set=lambda msg: setattr(self, "info", msg))
        self.errors = []

    def _post_to_main(self, fn):
        fn()

    def set_export_error(self, msg):
        self.errors.append(msg)

    def set_export_status(self, root, parts, cfg):
        self.exported_to = root


class ResolveExportRootTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.actions = _Actions(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def assertRefused(self, parent, name):
        with self.assertRaises(UnsafeExportDirError):
            self.actions.resolve_user_export_root(Path(parent), name)

    def test_dot_and_traversal_names_are_refused(self):
        for name in (".", "..", "a/b", "..\\x", "  "):
            with self.subTest(name=name):
                self.assertRefused(self.actions.output_dir.parent, name)

    def test_ancestors_of_session_state_are_refused(self):
        projeto = self.actions.output_dir.parent
        self.assertRefused(projeto.parent, projeto.name)
        self.assertRefused(self.root, "state_saved")

    def test_source_dataset_and_inside_it_are_refused(self):
        self.assertRefused(self.root, "dataset")
        self.assertRefused(self.actions.data_root, "exportacao")

    def test_home_is_refused(self):
        home = Path.home().resolve()
        self.assertRefused(home.parent, home.name)

    def test_existing_user_folder_gets_a_new_timestamped_name(self):
        folder = _user_folder(self.root / "fotos")
        resolved = self.actions.resolve_user_export_root(self.root, "fotos")
        self.assertNotEqual(resolved, folder)
        self.assertTrue(resolved.name.startswith("fotos_"))

    def test_previous_inolabel_export_is_reused(self):
        previous = reset_export_dir(self.root / "exp")
        self.assertEqual(self.actions.resolve_user_export_root(self.root, "exp"), previous)


class PerformExportSafetyTest(unittest.TestCase):
    def _config(self, parent, name):
        return SimpleNamespace(
            formats=["yolo"], destination_parent=parent, folder_name=name,
            use_split=False, split_ratios=(0.8, 0.1, 0.1), augmentation=None,
        )

    def _actions(self, root):
        actions = _Actions(root)
        cv2.imwrite(str(actions.output_images_dir / "a.jpg"), np.zeros((10, 10, 3), dtype=np.uint8))
        payload = {
            "images": [{"id": 1, "file_name": "a.jpg", "width": 10, "height": 10}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [1, 1, 4, 4]}],
            "categories": [{"id": 1, "name": "obj"}],
        }
        actions.load_export_payload_from_state = lambda: payload
        return actions

    def test_dot_folder_name_keeps_project_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            actions = self._actions(Path(tmp))
            actions.perform_dataset_export(self._config(actions.output_dir.parent, "."))
            self.assertEqual(len(actions.errors), 1)
            self.assertTrue((actions.output_images_dir / "a.jpg").exists())

    def test_export_writes_marked_dataset_and_can_be_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actions = self._actions(root)
            for _ in range(2):
                actions.perform_dataset_export(self._config(root, "exp"))
            self.assertEqual(actions.errors, [])
            self.assertEqual(actions.exported_to, (root / "exp").resolve())
            self.assertTrue(is_inolabel_export(root / "exp"))
            self.assertTrue((root / "exp" / "data.yaml").exists())

    def test_existing_user_folder_is_never_touched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = _user_folder(root / "fotos")
            actions = self._actions(root)
            actions.perform_dataset_export(self._config(root, "fotos"))
            self.assertEqual(actions.errors, [])
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ["importante.txt"])
            self.assertNotEqual(actions.exported_to, folder.resolve())

    def test_legacy_internal_yolo_dir_is_still_synced(self):
        """Pasta yolo_dataset interna, criada antes do marcador, continua sendo atualizada."""
        with tempfile.TemporaryDirectory() as tmp:
            actions = _Actions(Path(tmp))
            actions.yolo_dataset_dir = actions.output_dir / "yolo_dataset"
            actions.yolo_dataset_dir.mkdir()
            (actions.yolo_dataset_dir / "data.yaml").write_text("names: {}\n", encoding="utf-8")
            actions.coco_detection_export_path = actions.output_dir / "nao_existe.json"
            actions.build_coco_payload = lambda: {
                "images": [], "annotations": [], "categories": [{"id": 1, "name": "obj"}],
            }
            actions.sync_export_metadata()
            self.assertTrue(is_inolabel_export(actions.yolo_dataset_dir))


# ── C2: estado ilegivel ──────────────────────────────────────────────────────

class ReadAnnotationStateTest(unittest.TestCase):
    def test_missing_file_is_a_new_session(self):
        self.assertIsNone(read_annotation_state(Path("/nao/existe.json")))
        self.assertIsNone(read_annotation_state(None))

    def test_valid_state_is_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "annotations.coco.json"
            path.write_text(json.dumps({"images": []}), encoding="utf-8")
            self.assertEqual(read_annotation_state(path), {"images": []})

    def test_corrupt_and_non_object_json_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "annotations.coco.json"
            for content in ('{"images": [', "[1, 2]"):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(AnnotationStateUnreadableError) as ctx:
                    read_annotation_state(path)
                self.assertEqual(ctx.exception.path, path)


class LoadersFailLoudlyTest(unittest.TestCase):
    """Os tres modos: estado corrompido levanta erro e o arquivo fica intacto."""

    def test_all_modes(self):
        for mixin in (SourceLoadingMixin, OBBCocoStorageMixin, KPCocoStorageMixin):
            with self.subTest(mode=mixin.__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "annotations.coco.json"
                path.write_text('{"images": [ truncado', encoding="utf-8")
                tool = type("Tool", (mixin,), {})()
                tool.annotations_path = path
                with self.assertRaises(AnnotationStateUnreadableError):
                    tool.load_existing_annotations()
                self.assertEqual(path.read_text(encoding="utf-8"), '{"images": [ truncado')


class AbortUnreadableStateTest(unittest.TestCase):
    def test_user_is_told_and_window_closes_without_saving(self):
        tool = CoreInitMixin.__new__(CoreInitMixin)
        tool.closed = False
        tool.window = mock.Mock()
        loading = mock.Mock()
        error = AnnotationStateUnreadableError(Path("/x/annotations.coco.json"), ValueError("ruim"))

        with mock.patch("app.annotation.state.core_init.messagebox") as box:
            tool._abort_unreadable_state(error, loading)

        loading.close.assert_called_once()
        box.showerror.assert_called_once()
        self.assertIn("annotations.coco.json", box.showerror.call_args[0][1])
        tool.window.destroy.assert_called_once()
        self.assertTrue(tool.closed)


if __name__ == "__main__":
    unittest.main()
