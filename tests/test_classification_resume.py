"""Projeto de classificação só é retomado para a mesma pasta de origem (não para uma subpasta nova)."""

import tempfile
import unittest
from pathlib import Path


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
