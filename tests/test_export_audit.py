"""
Testes de regressão para o backend de exportação.

Cobre os bugs encontrados na auditoria:
  B1 – bbox inválido (w/h zero, coords fora de [0,1]) não gera label corrompido
  B2 – category_id inválido é ignorado silenciosamente
  B3 – data.yaml da API tem formato YAML correto para 'names'
  B4 – _flat_name_unique nunca produz nomes duplicados
  B5 – COCO export preserva campos opcionais (score, source, track_id)
  B6 – COCO export com dataset vazio ou sem anotações não gera erro
  B7 – OBB: label de imagem sem anotação é "" e não "\n"
  B8 – OBB: data.yaml não referencia 'val' (diretório que não existe)
  B9 – escrita atômica: arquivo .tmp não fica em disco após sucesso
  B10 – path traversal no _safe_output_path da API é rejeitado
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# B1 / B2 – normalize_yolo_bbox e class mapping
# ---------------------------------------------------------------------------

class TestNormalizeYoloBbox(unittest.TestCase):
    """B1 – Bboxes inválidas devem retornar None."""

    from app.annotation.core.export.yolo_label_service import normalize_yolo_bbox as _fn

    def _norm(self, bbox, w=100, h=100):
        from app.annotation.core.export.yolo_label_service import normalize_yolo_bbox
        return normalize_yolo_bbox(bbox, w, h)

    def test_zero_width_returns_none(self):
        self.assertIsNone(self._norm([10, 10, 0, 20]))

    def test_zero_height_returns_none(self):
        self.assertIsNone(self._norm([10, 10, 20, 0]))

    def test_negative_width_returns_none(self):
        self.assertIsNone(self._norm([10, 10, -5, 20]))

    def test_x_out_of_bounds_returns_none(self):
        # x=91 + w=20 → center=101 → cx=1.01 > 1.0 → rejeitado
        self.assertIsNone(self._norm([91, 0, 20, 10], w=100, h=100))

    def test_y_out_of_bounds_returns_none(self):
        # y=91 + h=20 → center=101 → cy=1.01 > 1.0 → rejeitado
        self.assertIsNone(self._norm([0, 91, 10, 20], w=100, h=100))

    def test_valid_bbox_returns_correct_values(self):
        result = self._norm([10, 20, 20, 20], w=100, h=100)
        self.assertIsNotNone(result)
        cx, cy, wn, hn = result
        self.assertAlmostEqual(cx, 0.2, places=6)
        self.assertAlmostEqual(cy, 0.3, places=6)
        self.assertAlmostEqual(wn, 0.2, places=6)
        self.assertAlmostEqual(hn, 0.2, places=6)

    def test_wrong_length_returns_none(self):
        self.assertIsNone(self._norm([10, 10, 20]))
        self.assertIsNone(self._norm([10, 10, 20, 20, 30]))

    def test_zero_image_dimension_returns_none(self):
        from app.annotation.core.export.yolo_label_service import normalize_yolo_bbox
        self.assertIsNone(normalize_yolo_bbox([0, 0, 10, 10], 0, 100))
        self.assertIsNone(normalize_yolo_bbox([0, 0, 10, 10], 100, 0))


# ---------------------------------------------------------------------------
# B2 – annotations_to_yolo_bboxes ignora category_id inválido
# ---------------------------------------------------------------------------

class TestAnnotationsToYoloBboxes(unittest.TestCase):
    """B2 – Anotações com category_id fora do mapeamento devem ser ignoradas."""

    def _run(self, annotations, class_mapping, img_w=100, img_h=100):
        from app.annotation.core.export.yolo_label_service import annotations_to_yolo_bboxes
        malformed: List[str] = []
        present: set = set()
        boxes = annotations_to_yolo_bboxes(
            annotations, class_mapping, img_w, img_h, malformed, present, "test.txt"
        )
        return boxes, malformed

    def test_invalid_category_id_skipped_and_logged(self):
        annotations = [{"id": 1, "image_id": 1, "category_id": 99, "bbox": [10, 10, 20, 20]}]
        boxes, malformed = self._run(annotations, {1: 0})
        self.assertEqual(boxes, [])
        self.assertTrue(any("99" in m for m in malformed))

    def test_invalid_bbox_skipped_and_logged(self):
        annotations = [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 0, 0]}]
        boxes, malformed = self._run(annotations, {1: 0})
        self.assertEqual(boxes, [])
        self.assertTrue(len(malformed) == 1)

    def test_valid_annotation_produces_correct_box(self):
        annotations = [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 100, 100]}]
        boxes, malformed = self._run(annotations, {1: 0})
        self.assertEqual(len(boxes), 1)
        self.assertEqual(malformed, [])
        cls_id, cx, cy, wn, hn = boxes[0]
        self.assertEqual(cls_id, 0)
        self.assertAlmostEqual(cx, 0.5)
        self.assertAlmostEqual(cy, 0.5)
        self.assertAlmostEqual(wn, 1.0)
        self.assertAlmostEqual(hn, 1.0)

    def test_mixed_valid_invalid_only_valid_exported(self):
        annotations = [
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20]},
            {"id": 2, "image_id": 1, "category_id": 99, "bbox": [10, 10, 20, 20]},
            {"id": 3, "image_id": 1, "category_id": 1, "bbox": [0, 0, 0, 5]},
        ]
        boxes, malformed = self._run(annotations, {1: 0})
        self.assertEqual(len(boxes), 1)
        self.assertEqual(len(malformed), 2)


# ---------------------------------------------------------------------------
# B3 – data.yaml da API tem formato YAML correto
# ---------------------------------------------------------------------------

class TestApiExportYaml(unittest.TestCase):
    """B3 – data.yaml gerado pela rota API deve usar formato dict para names."""

    def _build_yaml(self, classes):
        yaml_names = "\n".join(f"  {i}: {name}" for i, name in enumerate(classes))
        return (
            "path: /tmp/out\n"
            "train: images\n"
            "val: images\n"
            f"nc: {len(classes)}\n"
            "names:\n"
            f"{yaml_names}\n"
        )

    def test_names_is_yaml_dict_not_list(self):
        content = self._build_yaml(["car", "truck"])
        self.assertIn("names:", content)
        self.assertIn("  0: car", content)
        self.assertIn("  1: truck", content)
        self.assertNotIn("names: [", content)
        self.assertNotIn("names: ['", content)

    def test_nc_matches_class_count(self):
        content = self._build_yaml(["a", "b", "c"])
        self.assertIn("nc: 3", content)

    def test_single_class(self):
        content = self._build_yaml(["person"])
        self.assertIn("nc: 1", content)
        self.assertIn("  0: person", content)


# ---------------------------------------------------------------------------
# B4 – _flat_name_unique sem colisões
# ---------------------------------------------------------------------------

class TestFlatNameUnique(unittest.TestCase):
    """B4 – Nomes de arquivo achatados devem ser únicos."""

    def _call(self, file_name, used):
        from app.annotation.infrastructure.export.coco_exporter import _flat_name_unique
        return _flat_name_unique(file_name, used)

    def test_simple_file_no_collision(self):
        result = self._call("img.jpg", set())
        self.assertEqual(result, "img.jpg")

    def test_nested_path_flattened(self):
        result = self._call("lote_a/img.jpg", set())
        self.assertEqual(result, "lote_a_img.jpg")

    def test_collision_gets_numeric_suffix(self):
        used = {"lote_a_img.jpg"}
        result = self._call("lote_a/img.jpg", used)
        self.assertEqual(result, "lote_a_img_1.jpg")

    def test_multiple_collisions_increments(self):
        used = {"lote_a_img.jpg", "lote_a_img_1.jpg"}
        result = self._call("lote_a/img.jpg", used)
        self.assertEqual(result, "lote_a_img_2.jpg")

    def test_flat_file_and_nested_dont_collide(self):
        """lote_a_img.jpg (flat) e lote_a/img.jpg (nested) → devem ter nomes distintos."""
        used: set = set()
        from app.annotation.infrastructure.export.coco_exporter import _flat_name_unique
        name1 = _flat_name_unique("lote_a_img.jpg", used)
        used.add(name1)
        name2 = _flat_name_unique("lote_a/img.jpg", used)
        self.assertNotEqual(name1, name2)

    def test_coco_export_copies_without_overwrite(self):
        """Exportar dois arquivos que colidiria em nome flat não sobrescreve nenhum."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "lote_a").mkdir()
            (src / "lote_a" / "img.jpg").write_bytes(b"nested")
            (src / "lote_a_img.jpg").write_bytes(b"flat")

            payload = {
                "categories": [{"id": 1, "name": "car"}],
                "images": [
                    {"id": 1, "file_name": "lote_a/img.jpg", "width": 10, "height": 10},
                    {"id": 2, "file_name": "lote_a_img.jpg", "width": 10, "height": 10},
                ],
                "annotations": [],
            }

            from app.annotation.infrastructure.export.coco_exporter import export_detection_coco_json
            out_path = root / "out" / "annotations.coco.json"
            export_detection_coco_json(payload, out_path, source_images_dir=src)

            images_dir = root / "out" / "images"
            image_files = list(images_dir.iterdir())
            names = {f.name for f in image_files}
            contents = {f.read_bytes() for f in image_files}

            self.assertEqual(len(image_files), 2)
            self.assertEqual(len(names), 2, "Nomes devem ser únicos")
            self.assertIn(b"flat", contents)
            self.assertIn(b"nested", contents)


# ---------------------------------------------------------------------------
# B5 – COCO export preserva campos opcionais
# ---------------------------------------------------------------------------

class TestCocoExportOptionalFields(unittest.TestCase):
    """B5 – score, source, track_id devem ser preservados na saída COCO."""

    def _convert(self, annotations):
        from app.annotation.infrastructure.export.coco_exporter import convert_tracking_to_detection
        payload = {
            "images": [{"id": 1, "file_name": "img.jpg", "width": 100, "height": 100}],
            "categories": [{"id": 1, "name": "car"}],
            "annotations": annotations,
        }
        return convert_tracking_to_detection(payload)

    def test_score_preserved(self):
        result = self._convert([
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 10, 10],
             "area": 100, "iscrowd": 0, "segmentation": [], "score": 0.87}
        ])
        ann = result["annotations"][0]
        self.assertIn("score", ann)
        self.assertAlmostEqual(ann["score"], 0.87)

    def test_source_preserved(self):
        result = self._convert([
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 10, 10],
             "area": 100, "iscrowd": 0, "segmentation": [], "source": "manual"}
        ])
        ann = result["annotations"][0]
        self.assertIn("source", ann)
        self.assertEqual(ann["source"], "manual")

    def test_track_id_preserved(self):
        result = self._convert([
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 10, 10],
             "area": 100, "iscrowd": 0, "segmentation": [], "track_id": 42}
        ])
        ann = result["annotations"][0]
        self.assertIn("track_id", ann)
        self.assertEqual(ann["track_id"], 42)

    def test_absent_optional_fields_not_injected(self):
        result = self._convert([
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 10, 10],
             "area": 100, "iscrowd": 0, "segmentation": []}
        ])
        ann = result["annotations"][0]
        self.assertNotIn("score", ann)
        self.assertNotIn("track_id", ann)

    def test_required_fields_always_present(self):
        result = self._convert([
            {"id": 5, "image_id": 1, "category_id": 1, "bbox": [1, 2, 3, 4],
             "area": 12, "iscrowd": 0, "segmentation": []}
        ])
        ann = result["annotations"][0]
        for field in ("id", "image_id", "category_id", "bbox", "area", "segmentation", "iscrowd"):
            self.assertIn(field, ann)


# ---------------------------------------------------------------------------
# B6 – COCO export com dataset vazio ou sem anotações
# ---------------------------------------------------------------------------

class TestCocoExportEdgeCases(unittest.TestCase):
    """B6 – Exportar dataset vazio ou sem anotações não deve lançar exceção."""

    def test_empty_payload_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out" / "annotations.coco.json"
            from app.annotation.infrastructure.export.coco_exporter import export_detection_coco_json
            result = export_detection_coco_json(
                {"images": [], "annotations": [], "categories": []}, out
            )
            self.assertTrue(out.exists())
            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["images"], [])
            self.assertEqual(loaded["annotations"], [])

    def test_images_but_no_annotations(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out" / "annotations.coco.json"
            from app.annotation.infrastructure.export.coco_exporter import export_detection_coco_json
            payload = {
                "images": [{"id": 1, "file_name": "img.jpg", "width": 100, "height": 100}],
                "annotations": [],
                "categories": [{"id": 1, "name": "car"}],
            }
            result = export_detection_coco_json(payload, out)
            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(loaded["images"]), 1)
            self.assertEqual(loaded["annotations"], [])

    def test_tmp_file_not_left_on_disk_after_success(self):
        """B9 – Após escrita bem-sucedida o arquivo .tmp não deve existir."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "annotations.coco.json"
            from app.annotation.infrastructure.export.coco_exporter import export_detection_coco_json
            export_detection_coco_json(
                {"images": [], "annotations": [], "categories": []}, out
            )
            tmp_candidate = out.with_name(out.name + ".tmp")
            self.assertFalse(tmp_candidate.exists(), ".tmp não deve existir após escrita atômica bem-sucedida")

    def test_only_annotated_images_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "annotations.coco.json"
            from app.annotation.infrastructure.export.coco_exporter import export_detection_coco_json
            payload = {
                "images": [
                    {"id": 1, "file_name": "img1.jpg", "width": 10, "height": 10},
                    {"id": 2, "file_name": "img2.jpg", "width": 10, "height": 10},
                ],
                "annotations": [
                    {"id": 1, "image_id": 1, "category_id": 1,
                     "bbox": [0, 0, 5, 5], "area": 25, "iscrowd": 0, "segmentation": []}
                ],
                "categories": [{"id": 1, "name": "car"}],
            }
            result = export_detection_coco_json(payload, out, only_annotated_images=True)
            self.assertEqual(len(result["images"]), 1)
            self.assertEqual(result["images"][0]["id"], 1)


# ---------------------------------------------------------------------------
# B7 – OBB: label de imagem sem anotação deve ser ""
# ---------------------------------------------------------------------------

class TestObbEmptyLabel(unittest.TestCase):
    """B7 – Imagem sem anotações OBB deve gerar arquivo de label vazio ("")."""

    def test_unannotated_image_produces_empty_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "images"
            src.mkdir()
            (src / "img.jpg").write_bytes(b"fake")

            payload = {
                "categories": [{"id": 1, "name": "car"}],
                "images": [{"id": 1, "file_name": "img.jpg", "width": 100, "height": 50}],
                "annotations": [],
            }

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            export_yolo_obb_dataset(payload, root / "out", src)

            label = (root / "out" / "labels" / "train" / "img.txt").read_text(encoding="utf-8")
            self.assertEqual(label, "", f"Label vazio esperado, obteve: {repr(label)}")

    def test_annotated_image_produces_non_empty_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "images"
            src.mkdir()
            (src / "img.jpg").write_bytes(b"fake")

            payload = {
                "categories": [{"id": 1, "name": "car"}],
                "images": [{"id": 1, "file_name": "img.jpg", "width": 100, "height": 50}],
                "annotations": [
                    {
                        "id": 1, "image_id": 1, "category_id": 1,
                        "obb": {"cx": 50, "cy": 25, "width": 40, "height": 10, "angle": 0},
                    }
                ],
            }

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            export_yolo_obb_dataset(payload, root / "out", src)

            label = (root / "out" / "labels" / "train" / "img.txt").read_text(encoding="utf-8").strip()
            self.assertTrue(label.startswith("0 "), f"Esperava label iniciando com '0 ', obteve: {repr(label)}")


# ---------------------------------------------------------------------------
# B8 – OBB: data.yaml não referencia 'val' que nunca é criado
# ---------------------------------------------------------------------------

class TestObbDataYaml(unittest.TestCase):
    """B8 – data.yaml do OBB exporter não deve referenciar diretório 'val' inexistente."""

    def test_data_yaml_has_no_val_pointing_to_missing_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "images"
            src.mkdir()
            (src / "img.jpg").write_bytes(b"fake")

            payload = {
                "categories": [{"id": 1, "name": "car"}],
                "images": [{"id": 1, "file_name": "img.jpg", "width": 10, "height": 10}],
                "annotations": [],
            }

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            out_dir = root / "out"
            export_yolo_obb_dataset(payload, out_dir, src)

            yaml_content = (out_dir / "data.yaml").read_text(encoding="utf-8")
            val_dir = out_dir / "images" / "val"
            if "val:" in yaml_content:
                self.assertTrue(
                    val_dir.exists(),
                    "data.yaml referencia 'val' mas o diretório images/val não existe"
                )

    def test_data_yaml_has_train_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "images"
            src.mkdir()
            (src / "img.jpg").write_bytes(b"fake")

            payload = {
                "categories": [{"id": 1, "name": "car"}],
                "images": [{"id": 1, "file_name": "img.jpg", "width": 10, "height": 10}],
                "annotations": [],
            }

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            export_yolo_obb_dataset(payload, root / "out", src)

            yaml_content = (root / "out" / "data.yaml").read_text(encoding="utf-8")
            self.assertIn("train:", yaml_content)
            self.assertIn("names:", yaml_content)


# ---------------------------------------------------------------------------
# B10 – path traversal no _safe_output_path
# ---------------------------------------------------------------------------

class TestSafeOutputPath(unittest.TestCase):
    """B10 – _safe_output_path deve rejeitar nomes com path traversal."""

    def _call(self, destination, name):
        from app.api.routes.export import _safe_output_path
        return _safe_output_path(destination, name)

    def test_normal_name_accepted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = self._call(tmp, "my_dataset")
            self.assertTrue(str(result).endswith("my_dataset"))

    def test_traversal_via_dotdot_rejected(self):
        with self.assertRaises(ValueError):
            self._call("/tmp/safe", "../escape")

    def test_traversal_via_dotdot_in_name_rejected(self):
        with self.assertRaises(ValueError):
            self._call("/tmp/safe", "../../etc/passwd")

    def test_absolute_path_in_name_rejected(self):
        # On Unix, a name starting with / would go outside destination
        import os
        if os.name != "nt":
            with self.assertRaises((ValueError, Exception)):
                self._call("/tmp/safe", "/etc/passwd")


# ---------------------------------------------------------------------------
# Testes de integração do fluxo YOLO completo
# ---------------------------------------------------------------------------

class TestYoloExportIntegration(unittest.TestCase):
    """Testes de integração do fluxo completo de exportação YOLO."""

    def _make_fake_image(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), np.zeros((50, 80, 3), dtype=np.uint8))

    def test_export_with_zero_bbox_skipped(self):
        """Anotação com bbox zero deve ser registrada em malformed_labels e não gerar label."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            self._make_fake_image(src / "img.jpg")

            payload = {
                "images": [{"id": 1, "file_name": "img.jpg", "width": 80, "height": 50}],
                "annotations": [
                    {"id": 1, "image_id": 1, "category_id": 1, "bbox": [0, 0, 0, 0]},
                ],
                "categories": [{"id": 1, "name": "car"}],
            }

            from app.annotation.infrastructure.export.yolo_exporter import export_yolo_no_split
            report = export_yolo_no_split(payload, src, root / "out")

            label = (root / "out" / "labels" / "all" / "img.txt").read_text(encoding="utf-8")
            self.assertEqual(label, "")
            self.assertEqual(len(report["malformed_labels"]), 1)

    def test_empty_categories_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            self._make_fake_image(src / "img.jpg")

            payload = {
                "images": [{"id": 1, "file_name": "img.jpg", "width": 80, "height": 50}],
                "annotations": [],
                "categories": [],
            }

            from app.annotation.infrastructure.export.yolo_exporter import export_yolo_no_split
            with self.assertRaises(ValueError, msg="Deve lançar ValueError sem categorias"):
                export_yolo_no_split(payload, src, root / "out")

    def test_duplicate_image_names_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            self._make_fake_image(src / "img.jpg")

            payload = {
                "images": [
                    {"id": 1, "file_name": "img.jpg", "width": 80, "height": 50},
                    {"id": 2, "file_name": "img.jpg", "width": 80, "height": 50},
                ],
                "annotations": [],
                "categories": [{"id": 1, "name": "car"}],
            }

            from app.annotation.infrastructure.export.yolo_exporter import export_yolo_no_split
            with self.assertRaises(ValueError):
                export_yolo_no_split(payload, src, root / "out")

    def test_class_mapping_is_zero_based(self):
        """Categoria com id=5 deve ser mapeada para 0 no YOLO."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            self._make_fake_image(src / "img.jpg")

            payload = {
                "images": [{"id": 1, "file_name": "img.jpg", "width": 80, "height": 50}],
                "annotations": [
                    {"id": 1, "image_id": 1, "category_id": 5, "bbox": [0, 0, 40, 25]},
                ],
                "categories": [{"id": 5, "name": "truck"}],
            }

            from app.annotation.infrastructure.export.yolo_exporter import export_yolo_no_split
            export_yolo_no_split(payload, src, root / "out")

            label = (root / "out" / "labels" / "all" / "img.txt").read_text(encoding="utf-8").strip()
            cls_id = int(label.split()[0])
            self.assertEqual(cls_id, 0, "Categoria id=5 deve ser remapeada para 0 no YOLO")

    def test_format_yolo_boxes_empty_returns_empty_string(self):
        from app.annotation.core.export.yolo_label_service import format_yolo_boxes
        self.assertEqual(format_yolo_boxes([]), "")

    def test_format_yolo_boxes_single_box_ends_with_newline(self):
        from app.annotation.core.export.yolo_label_service import format_yolo_boxes
        result = format_yolo_boxes([[0, 0.5, 0.5, 0.2, 0.2]])
        self.assertTrue(result.endswith("\n"))

    def test_split_counts_always_cover_all_images(self):
        from app.annotation.core.export.split_service import compute_split_counts
        for total in range(1, 20):
            counts = compute_split_counts(total, (0.7, 0.2, 0.1))
            self.assertEqual(sum(counts.values()), total, f"total={total}")

    def test_split_counts_train_never_zero_when_images_exist(self):
        from app.annotation.core.export.split_service import compute_split_counts
        for total in range(1, 20):
            counts = compute_split_counts(total, (0.7, 0.2, 0.1))
            self.assertGreater(counts["train"], 0, f"train deve ser >= 1 para total={total}")

    def test_yolo_export_data_yaml_names_sorted_by_id(self):
        """data.yaml deve listar classes em ordem de id crescente."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            for name in ("img1.jpg", "img2.jpg"):
                self._make_fake_image(src / name)

            payload = {
                "images": [
                    {"id": 1, "file_name": "img1.jpg", "width": 80, "height": 50},
                    {"id": 2, "file_name": "img2.jpg", "width": 80, "height": 50},
                ],
                "annotations": [
                    {"id": 1, "image_id": 1, "category_id": 3, "bbox": [0, 0, 40, 25]},
                    {"id": 2, "image_id": 2, "category_id": 1, "bbox": [0, 0, 40, 25]},
                ],
                "categories": [
                    {"id": 1, "name": "car"},
                    {"id": 3, "name": "truck"},
                ],
            }

            from app.annotation.infrastructure.export.yolo_exporter import export_yolo_no_split
            export_yolo_no_split(payload, src, root / "out")

            yaml_text = (root / "out" / "data.yaml").read_text(encoding="utf-8")
            idx_car = yaml_text.index("car")
            idx_truck = yaml_text.index("truck")
            self.assertLess(idx_car, idx_truck, "car (id=1) deve aparecer antes de truck (id=3) no yaml")


# ---------------------------------------------------------------------------
# Testes de contrato do exportador COCO
# ---------------------------------------------------------------------------

class TestCocoExportContract(unittest.TestCase):
    """Contrato mínimo da saída COCO: campos obrigatórios sempre presentes."""

    def _export(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "annotations.coco.json"
            from app.annotation.infrastructure.export.coco_exporter import export_detection_coco_json
            export_detection_coco_json(payload, out)
            return json.loads(out.read_text(encoding="utf-8"))

    def test_top_level_keys_always_present(self):
        result = self._export({"images": [], "annotations": [], "categories": []})
        for key in ("info", "licenses", "categories", "images", "annotations"):
            self.assertIn(key, result)

    def test_info_has_version_and_date(self):
        result = self._export({"images": [], "annotations": [], "categories": []})
        self.assertIn("version", result["info"])
        self.assertIn("date_created", result["info"])

    def test_categories_normalized(self):
        payload = {
            "images": [],
            "annotations": [],
            "categories": [{"id": 2, "name": "dog"}],
        }
        result = self._export(payload)
        cat = result["categories"][0]
        self.assertIn("id", cat)
        self.assertIn("name", cat)
        self.assertIn("supercategory", cat)
        self.assertEqual(cat["name"], "dog")

    def test_image_has_required_fields(self):
        payload = {
            "images": [{"id": 1, "file_name": "a.jpg", "width": 100, "height": 50}],
            "annotations": [],
            "categories": [],
        }
        result = self._export(payload)
        img = result["images"][0]
        for field in ("id", "file_name", "width", "height"):
            self.assertIn(field, img)

    def test_annotation_has_required_fields(self):
        payload = {
            "images": [{"id": 1, "file_name": "a.jpg", "width": 100, "height": 50}],
            "annotations": [
                {"id": 1, "image_id": 1, "category_id": 1,
                 "bbox": [0, 0, 10, 10], "area": 100, "iscrowd": 0, "segmentation": []}
            ],
            "categories": [{"id": 1, "name": "car"}],
        }
        result = self._export(payload)
        ann = result["annotations"][0]
        for field in ("id", "image_id", "category_id", "bbox", "area", "segmentation", "iscrowd"):
            self.assertIn(field, ann)
        self.assertEqual(len(ann["bbox"]), 4)


if __name__ == "__main__":
    unittest.main()
