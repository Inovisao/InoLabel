import tempfile
import unittest
from pathlib import Path

from app.core.session import AnnotationSessionConfig, AnnotationTaskMode, normalize_class_names


class SessionConfigTest(unittest.TestCase):
    def test_normalize_class_names_removes_empty_and_duplicates(self):
        self.assertEqual(normalize_class_names([" car ", "", "bus", "car"]), ("car", "bus"))

    def test_session_config_keeps_mode_and_paths(self):
        config = AnnotationSessionConfig(
            mode=AnnotationTaskMode.DETECTION,
            data_root=Path("images"),
            weights_path=Path("model.pt"),
            target_classes=("Documento",),
        )

        self.assertFalse(config.tracking_enabled)
        self.assertEqual(config.mode, AnnotationTaskMode.DETECTION)
        self.assertEqual(config.target_classes, ("Documento",))

    def test_session_config_preserves_selected_annotations_path(self):
        config = AnnotationSessionConfig(
            mode=AnnotationTaskMode.TRACKING,
            data_root=Path("images"),
            weights_path=Path("model.pt"),
            target_classes=("car",),
            annotations_path=Path("output/__annotations.coco.json"),
            resume_existing_annotations=True,
        )

        self.assertEqual(config.annotations_path, Path("output/__annotations.coco.json"))
        self.assertEqual(config.weights_paths, (Path("model.pt"),))

    def test_session_requires_at_least_one_class(self):
        with self.assertRaises(ValueError):
            AnnotationSessionConfig(
                mode=AnnotationTaskMode.TRACKING,
                data_root=Path("images"),
                weights_path=Path("model.pt"),
                target_classes=("",),
            )

    def test_classification_session_does_not_require_weights(self):
        config = AnnotationSessionConfig(
            mode=AnnotationTaskMode.CLASSIFICATION,
            data_root=Path("images"),
            target_classes=("ok", "falha"),
        )

        self.assertEqual(config.weights_paths, ())
        self.assertIsNone(config.weights_path)
        self.assertEqual(config.target_classes, ("ok", "falha"))

    def test_classification_session_preserves_move_option(self):
        config = AnnotationSessionConfig(
            mode=AnnotationTaskMode.CLASSIFICATION,
            data_root=Path("images"),
            target_classes=("ok",),
            classification_move_files=True,
        )

        self.assertTrue(config.classification_move_files)


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
