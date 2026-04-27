import tempfile
import unittest
from pathlib import Path

from app.core.session import AnnotationTaskMode
from app.core.startup_cache import load_startup_cache, save_startup_cache


class StartupCacheTest(unittest.TestCase):
    def test_missing_cache_returns_empty_values(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = load_startup_cache(Path(tmp_dir) / "missing.json")

            self.assertIsNone(cache.data_root)
            self.assertIsNone(cache.weights_path)
            self.assertIsNone(cache.mode)

    def test_save_and_load_startup_cache(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "startup_cache.json"

            save_startup_cache(
                data_root=Path("/tmp/dataset"),
                weights_path=Path("/tmp/model.pt"),
                mode=AnnotationTaskMode.DETECTION,
                path=path,
            )
            cache = load_startup_cache(path)

            self.assertEqual(cache.data_root, Path("/tmp/dataset"))
            self.assertEqual(cache.weights_path, Path("/tmp/model.pt"))
            self.assertEqual(cache.mode, AnnotationTaskMode.DETECTION)


if __name__ == "__main__":
    unittest.main()
