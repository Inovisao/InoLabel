import tempfile
import unittest
from pathlib import Path

from app.core.session import AnnotationSessionConfig, AnnotationTaskMode, normalize_class_names
from app.sources.discovery import SourceDiscoveryService


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


class SourceDiscoveryServiceTest(unittest.TestCase):
    def test_discovers_image_directory_as_single_sequence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "a.jpg").write_bytes(b"fake")
            (root / "nested").mkdir()
            (root / "nested" / "b.png").write_bytes(b"fake")

            summary = SourceDiscoveryService().summarize(root)

            self.assertEqual(summary.sources, [root])
            self.assertEqual(summary.image_count, 2)
            self.assertEqual(summary.video_count, 0)

    def test_prefers_videos_when_directory_has_videos(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video = root / "clip.mp4"
            video.write_bytes(b"fake")
            (root / "a.jpg").write_bytes(b"fake")

            summary = SourceDiscoveryService().summarize(root)

            self.assertEqual(summary.sources, [video])
            self.assertEqual(summary.video_count, 1)


if __name__ == "__main__":
    unittest.main()
