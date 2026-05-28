import tempfile
import unittest
from pathlib import Path

from backend.core.startup_cache import load_startup_cache, save_startup_cache


class StartupCacheTest(unittest.TestCase):
    def test_missing_cache_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = load_startup_cache(Path(tmp_dir) / "missing.json")
            self.assertIsInstance(cache, dict)
            self.assertEqual(cache, {})

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "startup_cache.json"
            payload = {
                "mode": "detection",
                "data_root": "/tmp/dataset",
                "weights_paths": ["/tmp/model.pt"],
            }
            save_startup_cache(payload, path=path)
            loaded = load_startup_cache(path)
            self.assertEqual(loaded["mode"], "detection")
            self.assertEqual(loaded["data_root"], "/tmp/dataset")
            self.assertEqual(loaded["weights_paths"], ["/tmp/model.pt"])

    def test_malformed_json_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "bad.json"
            path.write_text("{invalid", encoding="utf-8")
            cache = load_startup_cache(path)
            self.assertIsInstance(cache, dict)
            self.assertEqual(cache, {})

    def test_save_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "nested" / "deep" / "cache.json"
            save_startup_cache({"mode": "tracking"}, path=path)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
