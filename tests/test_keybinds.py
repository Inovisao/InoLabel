import tempfile
import unittest
from pathlib import Path

from app.annotation.keybinds.actions import ACTION_REGISTRY
from app.annotation.keybinds.keybind_map import KeybindMap
from app.annotation.keybinds.keybind_repository import KeybindRepository


class KeybindMapTest(unittest.TestCase):
    def _make(self, name="test", **bindings) -> KeybindMap:
        return KeybindMap(name=name, bindings=dict(bindings))

    def test_get_key_returns_bound_key(self):
        km = self._make(next_frame="Right", prev_frame="Left")
        self.assertEqual(km.get_key("next_frame"), "Right")

    def test_get_key_returns_none_for_unset(self):
        km = self._make()
        self.assertIsNone(km.get_key("nonexistent"))

    def test_set_key_updates_binding(self):
        km = self._make(next_frame="Right")
        km.set_key("next_frame", "d")
        self.assertEqual(km.get_key("next_frame"), "d")

    def test_conflicts_with_finds_conflict(self):
        km = self._make(next_frame="d", prev_frame="a")
        conflict = km.conflicts_with("d", exclude_action="prev_frame")
        self.assertEqual(conflict, "next_frame")

    def test_conflicts_with_no_conflict(self):
        km = self._make(next_frame="d", prev_frame="a")
        conflict = km.conflicts_with("s", exclude_action="next_frame")
        self.assertIsNone(conflict)

    def test_conflicts_with_excludes_own_action(self):
        km = self._make(next_frame="d")
        # rebinding next_frame to the same key it already has — not a conflict with itself
        conflict = km.conflicts_with("d", exclude_action="next_frame")
        self.assertIsNone(conflict)

    def test_conflicts_with_empty_key_returns_none(self):
        km = self._make(next_frame="d")
        self.assertIsNone(km.conflicts_with("", exclude_action="prev_frame"))

    def test_copy_is_independent(self):
        km = self._make(next_frame="Right")
        km2 = km.copy()
        km2.set_key("next_frame", "d")
        self.assertEqual(km.get_key("next_frame"), "Right")
        self.assertEqual(km2.get_key("next_frame"), "d")

    def test_to_dict(self):
        km = self._make(next_frame="Right", prev_frame="Left")
        d = km.to_dict()
        self.assertEqual(d, {"next_frame": "Right", "prev_frame": "Left"})


class KeybindRepositoryTest(unittest.TestCase):
    def _repo(self, tmp_dir: str) -> KeybindRepository:
        return KeybindRepository(path=Path(tmp_dir) / "keybinds.json")

    def test_load_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp)
            active, profiles = repo.load()
            self.assertEqual(active, "arrows")
            self.assertIn("arrows", profiles)
            self.assertIn("wasd", profiles)

    def test_defaults_match_action_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp)
            defaults = repo.get_defaults()
            arrows = defaults["arrows"]
            wasd = defaults["wasd"]
            for action in ACTION_REGISTRY:
                self.assertEqual(arrows.get_key(action.id), action.default_arrows)
                self.assertEqual(wasd.get_key(action.id), action.default_wasd)

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp)
            _, profiles = repo.load()
            profiles["arrows"].set_key("next_frame", "d")
            repo.save("arrows", profiles)

            active2, profiles2 = repo.load()
            self.assertEqual(active2, "arrows")
            self.assertEqual(profiles2["arrows"].get_key("next_frame"), "d")

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = KeybindRepository(path=Path(tmp) / "nested" / "keybinds.json")
            _, profiles = repo.load()
            repo.save("arrows", profiles)
            self.assertTrue((Path(tmp) / "nested" / "keybinds.json").exists())

    def test_custom_profile_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp)
            _, profiles = repo.load()
            custom = profiles["arrows"].copy()
            custom.name = "meu_perfil"
            custom.set_key("next_frame", "x")
            profiles["meu_perfil"] = custom
            repo.save("meu_perfil", profiles)

            active2, profiles2 = repo.load()
            self.assertEqual(active2, "meu_perfil")
            self.assertIn("meu_perfil", profiles2)
            self.assertEqual(profiles2["meu_perfil"].get_key("next_frame"), "x")

    def test_malformed_json_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "keybinds.json"
            path.write_text("{invalid json", encoding="utf-8")
            repo = KeybindRepository(path=path)
            active, profiles = repo.load()
            self.assertEqual(active, "arrows")
            self.assertIn("arrows", profiles)

    def test_is_builtin(self):
        self.assertTrue(KeybindRepository.is_builtin("arrows"))
        self.assertTrue(KeybindRepository.is_builtin("wasd"))
        self.assertFalse(KeybindRepository.is_builtin("meu_perfil"))
        self.assertFalse(KeybindRepository.is_builtin("custom"))

    def test_unknown_active_profile_falls_back_to_arrows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "keybinds.json"
            path.write_text('{"active_profile": "nonexistent", "profiles": {}}', encoding="utf-8")
            repo = KeybindRepository(path=path)
            active, _ = repo.load()
            self.assertEqual(active, "arrows")


class ActionRegistryTest(unittest.TestCase):
    def test_all_actions_have_unique_ids(self):
        ids = [a.id for a in ACTION_REGISTRY]
        self.assertEqual(len(ids), len(set(ids)), "ACTION_REGISTRY has duplicate ids")

    def test_all_actions_have_labels_and_groups(self):
        for action in ACTION_REGISTRY:
            self.assertTrue(action.label, f"Action {action.id} has empty label")
            self.assertTrue(action.group, f"Action {action.id} has empty group")
            self.assertTrue(action.handler, f"Action {action.id} has empty handler")

    def test_toggle_edit_id_is_tracking_only(self):
        toggle = next((a for a in ACTION_REGISTRY if a.id == "toggle_edit_id"), None)
        self.assertIsNotNone(toggle)
        self.assertTrue(toggle.tracking_only)

    def test_wasd_default_has_no_toggle_selection(self):
        toggle = next((a for a in ACTION_REGISTRY if a.id == "toggle_selection"), None)
        self.assertIsNotNone(toggle)
        self.assertEqual(toggle.default_wasd, "", "toggle_selection deve ter binding vazio no perfil wasd")


if __name__ == "__main__":
    unittest.main()
