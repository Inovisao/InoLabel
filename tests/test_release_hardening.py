"""Pendencias da revisao 2.0: exportacao sem concorrencia (A2), versao (M2), logs sem
nomes de arquivo (M3), remocoes contidas na pasta (B1), merge protegido e utilitarios
executaveis como script."""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from app import __version__
from app.annotation.application.lifecycle import LifecycleMixin
from app.annotation.core.services.class_service import ClassServiceMixin
from app.annotation.infrastructure.export.export_dir import UnsafeExportDirError
from app.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from app.annotation.infrastructure.persistence.export_actions import ExportActionsMixin
from app.annotation.infrastructure.persistence.safe_paths import contained_path
from app.annotation.presentation.export.export_screen import ExportScreenMixin
from app.annotation.ui.ui_controls import UIControlsMixin
from app.annotation_keypoint.infrastructure.persistence.coco_storage import KPCocoStorageMixin
from app.annotation_keypoint.ui.ui_controls import KPUIControlsMixin
from app.annotation_obb.infrastructure.persistence.obb_coco_storage import OBBCocoStorageMixin
from app.annotation_obb.ui.ui_controls import OBBUIControlsMixin
from app.log_privacy import log_ref
from utils.merge_yolo_splits import merge_yolo_splits

ROOT = Path(__file__).resolve().parent.parent


# ── A2: exportacao sem concorrencia com a UI ─────────────────────────────────

class ShortcutsBlockedDuringExportTest(unittest.TestCase):
    def test_all_modes_ignore_shortcuts_on_export_screen(self):
        for mixin in (UIControlsMixin, OBBUIControlsMixin, KPUIControlsMixin):
            with self.subTest(mode=mixin.__name__):
                tool = type("Tool", (mixin,), {})()
                calls = []
                event = SimpleNamespace(widget=None)
                tool.export_screen_active = True
                tool._run_shortcut(event, lambda: calls.append("acao"))
                tool.export_screen_active = False
                tool._run_shortcut(event, lambda: calls.append("acao"))
                self.assertEqual(calls, ["acao"])

    def test_class_shortcut_ignored_on_export_screen(self):
        tool = type("Tool", (ClassServiceMixin,), {})()
        tool.window = SimpleNamespace(focus_get=lambda: None)
        tool.select_class_by_index = mock.Mock()
        tool.export_screen_active = True
        tool.on_class_shortcut(SimpleNamespace(char="2"))
        tool.select_class_by_index.assert_not_called()
        tool.export_screen_active = False
        tool.on_class_shortcut(SimpleNamespace(char="2"))
        tool.select_class_by_index.assert_called_once_with(1)


class ExportSnapshotOnUiThreadTest(unittest.TestCase):
    def test_confirm_loads_payload_before_starting_worker(self):
        """O autosave acontece na thread da UI; o worker recebe o payload pronto."""
        order = []

        class Screen(ExportScreenMixin):
            pass

        screen = Screen()
        screen._export_dest_var = SimpleNamespace(get=lambda: "/tmp")
        screen._export_folder_var = SimpleNamespace(get=lambda: "exp")
        screen._export_yolo_var = SimpleNamespace(get=lambda: True)
        screen._export_coco_var = SimpleNamespace(get=lambda: False)
        screen._export_split_var = SimpleNamespace(get=lambda: False)
        for name in ("_export_train_var", "_export_val_var", "_export_test_var"):
            setattr(screen, name, SimpleNamespace(get=lambda: "0.5"))
        screen._build_export_preset = lambda: None
        screen.load_export_payload_from_state = lambda: order.append("payload") or {"images": [1]}
        screen._export_status_var = mock.Mock()
        screen._export_status_label = mock.Mock()
        screen._export_confirm_btn = mock.Mock()
        screen._start_export_progress = lambda: None
        screen.window = mock.Mock()

        started = {}

        class FakeThread:
            def __init__(self, target, args, daemon):
                started["args"] = args

            def start(self):
                order.append("thread")

        with mock.patch("app.annotation.presentation.export.export_screen.threading.Thread", FakeThread):
            screen._confirm_export_screen()

        self.assertEqual(order, ["payload", "thread"])
        self.assertEqual(started["args"][1], {"images": [1]})

    def test_perform_uses_given_payload_without_autosave(self):
        class Actions(ExportActionsMixin):
            pass

        actions = Actions()
        actions.load_export_payload_from_state = mock.Mock(side_effect=AssertionError("autosave no worker"))
        actions._post_to_main = lambda fn: fn()
        actions.info_var = mock.Mock()
        actions.set_export_status = mock.Mock()
        actions.set_export_error = mock.Mock()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actions.output_dir = root / "proj" / "out"
            actions.output_images_dir = actions.output_dir / "images"
            actions.output_images_dir.mkdir(parents=True)
            config = SimpleNamespace(formats=["coco"], destination_parent=root, folder_name="exp",
                                     use_split=False, split_ratios=(1, 0, 0), augmentation=None)
            payload = {"images": [], "annotations": [], "categories": [{"id": 1, "name": "a"}]}
            actions.perform_dataset_export(config, payload=payload)
        actions.load_export_payload_from_state.assert_not_called()
        actions.set_export_error.assert_not_called()


# ── M2: versao ───────────────────────────────────────────────────────────────

class VersionTest(unittest.TestCase):
    def test_version_is_2_0_0(self):
        self.assertEqual(__version__, "2.0.0")

    def test_requirements_are_pinned(self):
        lines = [
            line.strip() for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertTrue(lines)
        for line in lines:
            self.assertIn("==", line, line)

    def test_coco_payload_records_app_version(self):
        for mixin in (CocoStorageMixin, OBBCocoStorageMixin, KPCocoStorageMixin):
            with self.subTest(mode=mixin.__name__):
                storage = type("S", (mixin,), {
                    "normalize_category_ids": lambda self: None,
                    "ensure_category_metadata": lambda self: None,
                    "ensure_keypoint_metadata": lambda self: None,
                })()
                storage.task_mode = SimpleNamespace(value="detection")
                storage.data_root = Path("/dados")
                storage.video_files = []
                storage.categories = storage.images = storage.annotations = []
                self.assertEqual(storage.build_coco_payload()["info"]["app_version"], "2.0.0")


# ── M3: logs sem nomes de arquivo ────────────────────────────────────────────

class LogPrivacyTest(unittest.TestCase):
    def test_log_ref_hides_name_and_is_stable(self):
        ref = log_ref("pessoas/joao_silva_01.jpg")
        self.assertNotIn("joao", ref)
        self.assertNotIn("silva", ref)
        self.assertEqual(ref, log_ref("pessoas/joao_silva_01.jpg"))
        self.assertNotEqual(ref, log_ref("pessoas/maria_02.jpg"))

    def test_autosave_log_has_no_file_name(self):
        class Tool(LifecycleMixin):
            pass

        tool = Tool()
        tool.current_frame = np.zeros((4, 4, 3), dtype=np.uint8)
        tool.closed = False
        tool.review_idx = None
        tool.saved_records = []
        tool.current_frame_file_name = lambda: "joao_silva_01.jpg"
        tool.find_image_record_by_file_name = lambda name: None
        tool.detections_to_save = lambda: []
        tool.store_annotations = lambda dets, existing_image_id=None, existing_file_name=None: (7, "joao_silva_01.jpg")
        tool.write_annotations = lambda: None
        tool.update_manual_memory_after_accept = lambda dets: None
        tool.remember_saved_record = lambda *a: None

        out = io.StringIO()
        with redirect_stdout(out):
            tool.autosave_current_frame(reason="teste")
        self.assertIn("image_id=7", out.getvalue())
        self.assertNotIn("joao", out.getvalue())


# ── B1: remocoes contidas na pasta ───────────────────────────────────────────

class ContainedPathTest(unittest.TestCase):
    def test_rejects_escape_absolute_and_empty(self):
        base = Path("/projeto/images")
        for rel in ("../segredo.txt", "a/../../x", "/etc/passwd", "", "."):
            with self.subTest(rel=rel):
                self.assertIsNone(contained_path(base, rel))
        self.assertEqual(contained_path(base, "lote/a.jpg"), Path("/projeto/images/lote/a.jpg").resolve())

    def test_remove_image_file_never_leaves_output_dir(self):
        for mixin in (CocoStorageMixin, OBBCocoStorageMixin, KPCocoStorageMixin):
            with self.subTest(mode=mixin.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                outside = root / "fora.txt"
                outside.write_text("x", encoding="utf-8")
                storage = type("S", (mixin,), {})()
                storage.output_images_dir = root / "out" / "images"
                storage.output_images_dir.mkdir(parents=True)
                self.assertFalse(storage.remove_image_file("../../fora.txt"))
                self.assertTrue(outside.exists())

    def test_remove_exported_files_never_leaves_dataset(self):
        for mixin in (CocoStorageMixin, OBBCocoStorageMixin):
            with self.subTest(mode=mixin.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                outside = root / "fora.jpg"
                outside.write_text("x", encoding="utf-8")
                storage = type("S", (mixin,), {})()
                storage.yolo_dataset_dir = root / "yolo"
                storage.remove_exported_dataset_files("../../../fora.jpg")
                self.assertTrue(outside.exists())


# ── Utilitarios ──────────────────────────────────────────────────────────────

class MergeSplitsGuardTest(unittest.TestCase):
    def test_merge_refuses_to_wipe_unrelated_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "yolo"
            (src / "images" / "train").mkdir(parents=True)
            (src / "labels" / "train").mkdir(parents=True)
            (src / "data.yaml").write_text("names:\n  0: obj\n", encoding="utf-8")
            target = root / "meus_arquivos"
            target.mkdir()
            (target / "importante.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(UnsafeExportDirError):
                merge_yolo_splits(src, target)
            self.assertTrue((target / "importante.txt").exists())


class UtilsRunAsScriptTest(unittest.TestCase):
    """O README manda rodar `python utils/<script>.py`; antes isso quebrava em `import app`."""

    def test_help_runs(self):
        for name in ("convert_coco_to_yolo_dataset", "convert_coco_tracking_to_detection",
                     "augment_output_dataset", "merge_yolo_splits"):
            with self.subTest(script=name):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "utils" / f"{name}.py"), "--help"],
                    cwd=str(ROOT / "utils"), capture_output=True, text=True, timeout=120,
                )
                self.assertEqual(result.returncode, 0, result.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
