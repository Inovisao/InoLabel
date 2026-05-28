import tempfile
import unittest
import json
from pathlib import Path

from backend.classification.dataset import (
    STATE_FILE_NAME,
    ClassificationRecord,
    add_class_directory,
    class_directories_for,
    class_directory_has_files,
    classify_image_source,
    copy_image_to_class,
    discover_images,
    export_classification_dataset,
    load_state,
    latest_output_state_for_sources,
    list_output_states_for_sources,
    prepare_dataset,
    remove_class_directory,
    source_looks_used,
    transfer_image_to_class,
    sanitize_class_dir_name,
    write_state,
)


class ClassificationDatasetTest(unittest.TestCase):
    def test_sanitizes_class_directory_names(self):
        self.assertEqual(sanitize_class_dir_name(" Classe Boa "), "classe_boa")
        self.assertEqual(sanitize_class_dir_name("A/B:C"), "a_b_c")

    def test_class_directories_are_unique_after_sanitization(self):
        directories = class_directories_for(["classe boa", "classe/boa", "classe boa"])

        self.assertEqual(directories, {"classe boa": "classe_boa", "classe/boa": "classe_boa_1"})

    def test_prepare_dataset_creates_class_subfolders(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir)

            directories = prepare_dataset(output, ["Ok", "Falha Grave"])

            self.assertEqual(directories["Ok"], "ok")
            self.assertTrue((output / "ok").is_dir())
            self.assertTrue((output / "falha_grave").is_dir())

    def test_add_class_directory_creates_unique_subfolder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir)
            directories = prepare_dataset(output, ["Classe Boa"])

            dirname = add_class_directory(output, "Classe/Boa", directories)

            self.assertEqual(dirname, "classe_boa_1")
            self.assertEqual(directories["Classe/Boa"], "classe_boa_1")
            self.assertTrue((output / "classe_boa_1").is_dir())

    def test_remove_class_directory_removes_empty_mapping_and_folder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir)
            directories = prepare_dataset(output, ["Ok"])

            removed = remove_class_directory(output, "Ok", directories)

            self.assertEqual(removed, output / "ok")
            self.assertNotIn("Ok", directories)
            self.assertFalse((output / "ok").exists())

    def test_remove_class_directory_keeps_non_empty_folder_by_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir)
            directories = prepare_dataset(output, ["Ok"])
            (output / "ok" / "img.jpg").write_bytes(b"image")

            self.assertTrue(class_directory_has_files(output, "Ok", directories))
            remove_class_directory(output, "Ok", directories)

            self.assertNotIn("Ok", directories)
            self.assertTrue((output / "ok" / "img.jpg").exists())

    def test_remove_class_directory_can_archive_non_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir)
            directories = prepare_dataset(output, ["Ok"])
            (output / "ok" / "img.jpg").write_bytes(b"image")

            remove_class_directory(output, "Ok", directories, archive_files=True)

            self.assertNotIn("Ok", directories)
            self.assertFalse((output / "ok").exists())
            self.assertTrue((output / "_removed" / "ok" / "img.jpg").exists())

    def test_remove_class_directory_can_delete_non_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir)
            directories = prepare_dataset(output, ["Ok"])
            (output / "ok" / "img.jpg").write_bytes(b"image")

            remove_class_directory(output, "Ok", directories, delete_files=True)

            self.assertNotIn("Ok", directories)
            self.assertFalse((output / "ok").exists())

    def test_copy_image_to_class_avoids_name_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "source" / "img.jpg"
            source.parent.mkdir()
            source.write_bytes(b"original")
            output = root / "output"
            directories = prepare_dataset(output, ["Ok"])
            (output / "ok" / "img.jpg").write_bytes(b"existing")

            record = copy_image_to_class(source, class_name="Ok", output_dir=output, class_directories=directories)

            self.assertEqual(record.destination_path.name, "img__001.jpg")
            self.assertEqual(record.destination_path.read_bytes(), b"original")
            self.assertEqual(record.operation, "copy")

    def test_move_image_to_class_removes_source(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "source" / "img.jpg"
            source.parent.mkdir()
            source.write_bytes(b"original")
            output = root / "output"
            directories = prepare_dataset(output, ["Ok"])

            record = transfer_image_to_class(
                source,
                class_name="Ok",
                output_dir=output,
                class_directories=directories,
                move=True,
            )

            self.assertFalse(source.exists())
            self.assertEqual(record.destination_path.read_bytes(), b"original")
            self.assertEqual(record.operation, "move")

    def test_classify_image_source_only_records_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "source" / "img.jpg"
            source.parent.mkdir()
            source.write_bytes(b"original")
            output = root / "output"
            directories = prepare_dataset(output, ["Ok"])

            record = classify_image_source(
                source,
                class_name="Ok",
                output_dir=output,
                class_directories=directories,
            )

            self.assertTrue(source.exists())
            self.assertFalse(record.destination_path.exists())
            self.assertEqual(record.destination_path, output / "ok" / "img.jpg")
            self.assertEqual(record.operation, "state")

    def test_export_classification_dataset_copies_records_to_class_folders(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source_a = root / "source" / "a.jpg"
            source_b = root / "source" / "nested" / "a.jpg"
            source_b.parent.mkdir(parents=True)
            source_a.write_bytes(b"a")
            source_b.write_bytes(b"b")
            output = root / "output"
            directories = prepare_dataset(output, ["Ok", "Falha"])
            records = [
                classify_image_source(source_a, class_name="Ok", output_dir=output, class_directories=directories),
                classify_image_source(source_b, class_name="Ok", output_dir=output, class_directories=directories),
            ]

            report = export_classification_dataset(
                records=records,
                classes=["Ok", "Falha"],
                class_directories=directories,
                dataset_root=root / "exported",
            )

            self.assertEqual(report["copied"], 2)
            self.assertEqual(report["skipped"], [])
            self.assertEqual((root / "exported" / "ok" / "a.jpg").read_bytes(), b"a")
            self.assertEqual((root / "exported" / "ok" / "a__001.jpg").read_bytes(), b"b")
            self.assertTrue((root / "exported" / "falha").is_dir())

    def test_source_looks_used_matches_original_and_conflict_names(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output = root / "output"
            directories = prepare_dataset(output, ["Ok"])
            (output / "ok" / "img__001.jpg").write_bytes(b"used")

            self.assertTrue(source_looks_used(root / "img.jpg", output, directories))
            self.assertFalse(source_looks_used(root / "other.jpg", output, directories))

    def test_discovers_images_from_folder_and_list(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            image_a = root / "a.jpg"
            image_b = root / "nested" / "b.png"
            image_b.parent.mkdir()
            image_a.write_bytes(b"a")
            image_b.write_bytes(b"b")
            listing = root / "images.txt"
            listing.write_text("a.jpg\nnested/b.png\n", encoding="utf-8")

            self.assertEqual(discover_images(listing), [image_a, image_b])
            self.assertEqual(discover_images(root), [image_a, image_b])

    def test_writes_and_loads_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            state_path = root / STATE_FILE_NAME
            record = ClassificationRecord(
                source_path=root / "source.jpg",
                destination_path=root / "ok" / "source.jpg",
                class_name="Ok",
                classified_at="2026-05-04T10:00:00",
                operation="move",
            )

            write_state(
                state_path,
                classes=["Ok"],
                class_directories={"Ok": "ok"},
                source_root=root,
                records=[record],
            )

            loaded = load_state(state_path)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.classes, ("Ok",))
            self.assertEqual(loaded.class_directories, {"Ok": "ok"})
            self.assertEqual(loaded.records, (record,))

    def test_rejects_coco_payload_as_classification_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / STATE_FILE_NAME
            state_path.write_text(
                json.dumps({"categories": [{"id": 1, "name": "obj"}], "images": [], "annotations": []}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_state(state_path)

    def test_rejects_non_classification_task_mode(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / STATE_FILE_NAME
            state_path.write_text(
                json.dumps({"task_mode": "detection", "classes": ["obj"], "records": []}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_state(state_path)

    def test_lists_classification_states_for_sources(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source_a = root / "source_a"
            source_b = root / "source_b"
            source_a.mkdir()
            source_b.mkdir()
            outputs = root / "outputs"
            old_output = outputs / "output_dataset1_20260504_100000"
            new_output = outputs / "output_dataset2_20260504_110000"
            old_output.mkdir(parents=True)
            new_output.mkdir(parents=True)
            write_state(
                old_output / STATE_FILE_NAME,
                classes=["Ok"],
                class_directories={"Ok": "ok"},
                source_root=source_a,
                records=[],
            )
            write_state(
                new_output / STATE_FILE_NAME,
                classes=["Falha"],
                class_directories={"Falha": "falha"},
                source_root=source_b,
                records=[],
            )

            states = list_output_states_for_sources([source_a], outputs)
            latest = latest_output_state_for_sources([source_a], outputs)

            self.assertEqual([state.path.name for state in states], [old_output.name])
            self.assertEqual(latest.path, old_output)
            self.assertEqual(latest.class_names, ("Ok",))

    def test_list_classification_states_skips_corrupt_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "source"
            source.mkdir()
            outputs = root / "outputs"
            bad_output = outputs / "output_dataset1_20260504_100000"
            good_output = outputs / "output_dataset2_20260504_110000"
            bad_output.mkdir(parents=True)
            good_output.mkdir(parents=True)
            (bad_output / STATE_FILE_NAME).write_text("{invalid", encoding="utf-8")
            write_state(
                good_output / STATE_FILE_NAME,
                classes=["Ok"],
                class_directories={"Ok": "ok"},
                source_root=source,
                records=[],
            )

            states = list_output_states_for_sources([source], outputs)

            self.assertEqual([state.path.name for state in states], [good_output.name])


if __name__ == "__main__":
    unittest.main()
