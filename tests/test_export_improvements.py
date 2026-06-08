"""
Testes de regressão para as melhorias de exportação:
  I1 – normalize_split_ratios em split_service (utilidade compartilhada)
  I2 – aviso antes de shutil.rmtree nos exporters YOLO
  I3 – OBB exporter com suporte a split (train/val/test)
  I4 – ExportJob armazena use_split e split_ratios
  I5 – start_export wira split_ratios no job
  I6 – _run_export constrói payload COCO e delega ao pipeline canônico
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# I1 – normalize_split_ratios em split_service
# ---------------------------------------------------------------------------

class TestNormalizeSplitRatios(unittest.TestCase):
    """I1 – normalize_split_ratios deve ser pública e acessível via split_service."""

    def _call(self, *args):
        from app.annotation.core.export.split_service import normalize_split_ratios
        return normalize_split_ratios(*args)

    def test_already_normalized_unchanged(self):
        result = self._call((0.7, 0.2, 0.1))
        self.assertAlmostEqual(sum(result), 1.0, places=10)
        self.assertAlmostEqual(result[0], 0.7, places=10)

    def test_unnormalized_sum_to_one_after_call(self):
        result = self._call((7.0, 2.0, 1.0))
        self.assertAlmostEqual(sum(result), 1.0, places=10)
        self.assertAlmostEqual(result[0], 0.7, places=10)

    def test_negative_ratio_raises(self):
        with self.assertRaises(ValueError):
            self._call((-0.1, 0.5, 0.6))

    def test_all_zero_raises(self):
        with self.assertRaises(ValueError):
            self._call((0.0, 0.0, 0.0))

    def test_wrong_length_raises(self):
        with self.assertRaises((ValueError, TypeError)):
            self._call((0.5, 0.5))

    def test_train_only_normalized(self):
        result = self._call((1.0, 0.0, 0.0))
        self.assertAlmostEqual(result[0], 1.0)
        self.assertAlmostEqual(result[1], 0.0)
        self.assertAlmostEqual(result[2], 0.0)

    def test_imported_in_yolo_exporter(self):
        """yolo_exporter deve re-usar normalize_split_ratios do split_service."""
        from app.annotation.core.export.split_service import normalize_split_ratios as ref
        from app.annotation.infrastructure.export.yolo_exporter import _normalized_split_ratios
        result_a = ref((8.0, 1.0, 1.0))
        result_b = _normalized_split_ratios((8.0, 1.0, 1.0))
        self.assertEqual(result_a, result_b)


# ---------------------------------------------------------------------------
# I2 – aviso antes de shutil.rmtree
# ---------------------------------------------------------------------------

class TestRmtreeWarning(unittest.TestCase):
    """I2 – Deve imprimir aviso [AVISO] antes de destruir um diretório existente."""

    def _make_fake_image(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), np.zeros((10, 10, 3), dtype=np.uint8))

    def test_warning_printed_on_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            self._make_fake_image(src / "img.jpg")
            dataset_root = root / "out"
            dataset_root.mkdir()  # pre-existing directory

            payload = {
                "images": [{"id": 1, "file_name": "img.jpg", "width": 10, "height": 10}],
                "annotations": [],
                "categories": [{"id": 1, "name": "car"}],
            }

            from app.annotation.infrastructure.export.yolo_exporter import export_yolo_no_split
            import io
            import sys
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                export_yolo_no_split(payload, src, dataset_root)

            output = captured.getvalue()
            self.assertIn("[AVISO]", output)
            self.assertIn(str(dataset_root), output)

    def test_no_warning_when_dir_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            self._make_fake_image(src / "img.jpg")
            dataset_root = root / "fresh_out"  # does NOT exist yet

            payload = {
                "images": [{"id": 1, "file_name": "img.jpg", "width": 10, "height": 10}],
                "annotations": [],
                "categories": [{"id": 1, "name": "car"}],
            }

            from app.annotation.infrastructure.export.yolo_exporter import export_yolo_no_split
            import io
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                export_yolo_no_split(payload, src, dataset_root)

            output = captured.getvalue()
            self.assertNotIn("[AVISO]", output)


# ---------------------------------------------------------------------------
# I3 – OBB exporter com suporte a split
# ---------------------------------------------------------------------------

class TestObbSplit(unittest.TestCase):
    """I3 – OBB exporter deve criar splits train/val/test quando split_ratios fornecido."""

    def _make_payload(self, n_images: int) -> dict:
        images = [
            {"id": i, "file_name": f"img_{i:03d}.jpg", "width": 100, "height": 50}
            for i in range(1, n_images + 1)
        ]
        annotations = [
            {
                "id": i,
                "image_id": i,
                "category_id": 1,
                "obb": {"cx": 50, "cy": 25, "width": 40, "height": 10, "angle": 0},
            }
            for i in range(1, n_images + 1)
        ]
        return {
            "categories": [{"id": 1, "name": "doc"}],
            "images": images,
            "annotations": annotations,
        }

    def _create_source_images(self, src_dir: Path, n: int):
        for i in range(1, n + 1):
            cv2.imwrite(str(src_dir / f"img_{i:03d}.jpg"), np.zeros((50, 100, 3), dtype=np.uint8))

    def test_no_split_puts_all_in_train(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            self._create_source_images(src, 4)

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            summary = export_yolo_obb_dataset(self._make_payload(4), root / "out", src)

            self.assertTrue((root / "out" / "images" / "train").exists())
            self.assertFalse((root / "out" / "images" / "val").exists())
            self.assertFalse((root / "out" / "images" / "test").exists())
            self.assertEqual(summary["images"], 4)

    def test_split_ratios_creates_correct_subdirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            self._create_source_images(src, 6)

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            summary = export_yolo_obb_dataset(
                self._make_payload(6), root / "out", src, split_ratios=(0.5, 0.25, 0.25)
            )

            self.assertTrue((root / "out" / "images" / "train").exists())
            self.assertTrue((root / "out" / "images" / "val").exists())
            self.assertTrue((root / "out" / "images" / "test").exists())
            total = sum(summary["images_per_split"].values())
            self.assertEqual(total, 6)

    def test_split_data_yaml_only_lists_used_splits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            self._create_source_images(src, 4)

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            export_yolo_obb_dataset(
                self._make_payload(4), root / "out", src, split_ratios=(0.5, 0.25, 0.25)
            )

            yaml_text = (root / "out" / "data.yaml").read_text(encoding="utf-8")
            for split in ("train", "val", "test"):
                split_dir = root / "out" / "images" / split
                if split_dir.exists() and any(split_dir.iterdir()):
                    self.assertIn(f"{split}:", yaml_text)

    def test_split_no_val_reference_when_no_split(self):
        """Sem split_ratios, data.yaml não deve referenciar val ou test."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            self._create_source_images(src, 3)

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            export_yolo_obb_dataset(self._make_payload(3), root / "out", src)

            yaml_text = (root / "out" / "data.yaml").read_text(encoding="utf-8")
            self.assertIn("train:", yaml_text)
            # val only appears if its directory has images
            val_dir = root / "out" / "images" / "val"
            if not val_dir.exists():
                self.assertNotIn("val:", yaml_text)

    def test_split_images_per_split_in_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            self._create_source_images(src, 10)

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            summary = export_yolo_obb_dataset(
                self._make_payload(10), root / "out", src, split_ratios=(0.7, 0.2, 0.1)
            )

            self.assertIn("images_per_split", summary)
            total = sum(summary["images_per_split"].values())
            self.assertEqual(total, 10)

    def test_backward_compat_no_split_ratios_returns_dict_with_images(self):
        """Chamadas sem split_ratios continuam funcionando."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "img.jpg").write_bytes(b"fake")

            payload = {
                "categories": [{"id": 2, "name": "doc"}],
                "images": [{"id": 1, "file_name": "img.jpg", "width": 100, "height": 50}],
                "annotations": [{
                    "id": 1, "image_id": 1, "category_id": 2,
                    "obb": {"cx": 50, "cy": 25, "width": 40, "height": 10, "angle": 0},
                }],
            }

            from app.annotation_obb.infrastructure.export.yolo_obb_exporter import export_yolo_obb_dataset
            summary = export_yolo_obb_dataset(payload, root / "out", src)
            self.assertIn("images", summary)
            self.assertEqual(summary["images"], 1)


# ---------------------------------------------------------------------------
# I4 – ExportJob armazena use_split e split_ratios
# ---------------------------------------------------------------------------

class TestExportJobFields(unittest.TestCase):
    """I4 – ExportJob deve ter use_split e split_ratios com defaults razoáveis."""

    def test_default_use_split_is_true(self):
        from app.core.exporter import ExportJob
        job = ExportJob(destination=Path("/tmp"), name="out", formats=["yolo"])
        self.assertTrue(job.use_split)

    def test_default_split_ratios_sum_to_one(self):
        from app.core.exporter import ExportJob
        job = ExportJob(destination=Path("/tmp"), name="out", formats=["yolo"])
        self.assertAlmostEqual(sum(job.split_ratios), 1.0, places=10)

    def test_custom_split_ratios_stored(self):
        from app.core.exporter import ExportJob
        job = ExportJob(
            destination=Path("/tmp"), name="out", formats=["yolo"],
            split_ratios=(0.6, 0.3, 0.1),
        )
        self.assertEqual(job.split_ratios, (0.6, 0.3, 0.1))

    def test_use_split_false_stored(self):
        from app.core.exporter import ExportJob
        job = ExportJob(
            destination=Path("/tmp"), name="out", formats=["yolo"], use_split=False
        )
        self.assertFalse(job.use_split)

    def test_output_path_unchanged(self):
        from app.core.exporter import ExportJob
        job = ExportJob(destination=Path("/tmp"), name="my_dataset", formats=["yolo"])
        self.assertEqual(job.output_path, Path("/tmp/my_dataset"))


# ---------------------------------------------------------------------------
# I5 – start_export wira split_ratios no job (via API contract)
# ---------------------------------------------------------------------------

class TestStartExportSplitWiring(unittest.TestCase):
    """I5 – split config do request deve ser gravada no ExportJob."""

    def setUp(self):
        from app.api.state import reset_state, create_session
        from pathlib import Path
        import tempfile
        reset_state()
        self._tmp = tempfile.mkdtemp()
        self._session = create_session(
            mode="detection",
            data_path=Path(self._tmp),
            output_path=Path(self._tmp),
            classes=["car", "truck"],
        )

    def tearDown(self):
        from app.api.state import reset_state
        import shutil
        reset_state()
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_split_ratios_stored_in_job(self):
        from fastapi.testclient import TestClient
        from app.api.main import app
        from app.api.state import _exports

        client = TestClient(app)
        resp = client.post("/api/export", json={
            "session_id": self._session.session_id,
            "destination": self._tmp,
            "name": "test_out",
            "formats": ["yolo"],
            "split": {"train": 0.6, "val": 0.3, "test": 0.1},
            "use_split": True,
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        export_id = resp.json()["export_id"]

        job = _exports[export_id]
        self.assertTrue(job.use_split)
        self.assertAlmostEqual(job.split_ratios[0], 0.6, places=5)
        self.assertAlmostEqual(job.split_ratios[1], 0.3, places=5)
        self.assertAlmostEqual(job.split_ratios[2], 0.1, places=5)

    def test_use_split_false_stored_in_job(self):
        from fastapi.testclient import TestClient
        from app.api.main import app
        from app.api.state import _exports

        client = TestClient(app)
        resp = client.post("/api/export", json={
            "session_id": self._session.session_id,
            "destination": self._tmp,
            "name": "test_out2",
            "formats": ["yolo"],
            "use_split": False,
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        export_id = resp.json()["export_id"]
        job = _exports[export_id]
        self.assertFalse(job.use_split)


# ---------------------------------------------------------------------------
# I6 – _run_export usa pipeline canônico (COCO payload + export_yolo_dataset)
# ---------------------------------------------------------------------------

class TestRunExportCanonicalPipeline(unittest.TestCase):
    """I6 – _run_export deve produzir estrutura de dataset YOLO válida via pipeline canônico."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()

    def _setup_session_with_frames(self, n_frames: int):
        """Cria sessão, frames e annotations no state em memória."""
        from app.api.state import reset_state, create_session, frame_paths, frame_dims, annotation_store, next_ann_id
        from app.api.schemas import Annotation

        reset_state()
        session = create_session(
            mode="detection",
            data_path=Path(self._tmp),
            output_path=Path(self._tmp),
            classes=["car"],
        )

        # Write real images and add to state
        for i in range(n_frames):
            img_path = Path(self._tmp) / f"frame_{i:03d}.jpg"
            cv2.imwrite(str(img_path), np.zeros((50, 80, 3), dtype=np.uint8))
            frame_paths.append(img_path)
            frame_dims[i] = (80, 50)
            annotation_store[i] = [
                Annotation(
                    id=next_ann_id[0],
                    image_id=i,
                    category_id=0,
                    bbox=[5.0, 5.0, 20.0, 15.0],
                )
            ]
            next_ann_id[0] += 1

        return session

    def tearDown(self):
        from app.api.state import reset_state
        import shutil
        reset_state()
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_export_with_split_creates_standard_yolo_structure(self):
        import asyncio
        from app.core.exporter import ExportJob
        from app.api.state import create_export

        session = self._setup_session_with_frames(6)
        out_dir = Path(self._tmp) / "dataset_out"
        job = create_export(ExportJob(
            destination=out_dir.parent,
            name=out_dir.name,
            formats=["yolo"],
            use_split=True,
            split_ratios=(0.5, 0.25, 0.25),
        ))

        from app.api.routes.export import _run_export
        asyncio.run(_run_export(job.export_id))

        self.assertEqual(job.status, "done")
        self.assertAlmostEqual(job.progress, 1.0)
        # Standard YOLO structure
        self.assertTrue((out_dir / "images" / "train").exists())
        self.assertTrue((out_dir / "labels" / "train").exists())
        self.assertTrue((out_dir / "data.yaml").exists())

        yaml_text = (out_dir / "data.yaml").read_text(encoding="utf-8")
        self.assertIn("train:", yaml_text)
        self.assertIn("names:", yaml_text)
        self.assertIn("  0: car", yaml_text)

    def test_run_export_no_split_creates_all_folder(self):
        import asyncio
        from app.core.exporter import ExportJob
        from app.api.state import create_export

        session = self._setup_session_with_frames(3)
        out_dir = Path(self._tmp) / "dataset_nosplit"
        job = create_export(ExportJob(
            destination=out_dir.parent,
            name=out_dir.name,
            formats=["yolo"],
            use_split=False,
        ))

        from app.api.routes.export import _run_export
        asyncio.run(_run_export(job.export_id))

        self.assertEqual(job.status, "done")
        self.assertTrue((out_dir / "images" / "all").exists())
        self.assertTrue((out_dir / "labels" / "all").exists())

    def test_run_export_label_content_valid_yolo(self):
        """Cada label deve ter format: class_id cx cy w h com valores em [0,1]."""
        import asyncio
        from app.core.exporter import ExportJob
        from app.api.state import create_export

        session = self._setup_session_with_frames(2)
        out_dir = Path(self._tmp) / "dataset_labels"
        job = create_export(ExportJob(
            destination=out_dir.parent,
            name=out_dir.name,
            formats=["yolo"],
            use_split=False,
        ))

        from app.api.routes.export import _run_export
        asyncio.run(_run_export(job.export_id))

        label_files = list((out_dir / "labels" / "all").rglob("*.txt"))
        self.assertEqual(len(label_files), 2)

        for lf in label_files:
            content = lf.read_text(encoding="utf-8").strip()
            if not content:
                continue
            parts = content.split()
            self.assertEqual(len(parts), 5, f"Formato inválido em {lf.name}: {content}")
            cls_id = int(parts[0])
            self.assertEqual(cls_id, 0)
            for val in parts[1:]:
                f = float(val)
                self.assertGreaterEqual(f, 0.0)
                self.assertLessEqual(f, 1.0)

    def test_run_export_empty_store_completes_without_error(self):
        """Store vazio deve terminar status=done sem criar estrutura de diretório."""
        import asyncio
        from app.api.state import reset_state, create_session
        from app.core.exporter import ExportJob
        from app.api.state import create_export

        reset_state()
        session = create_session(
            mode="detection",
            data_path=Path(self._tmp),
            output_path=Path(self._tmp),
            classes=["car"],
        )
        out_dir = Path(self._tmp) / "empty_out"
        job = create_export(ExportJob(
            destination=out_dir.parent,
            name=out_dir.name,
            formats=["yolo"],
        ))

        from app.api.routes.export import _run_export
        asyncio.run(_run_export(job.export_id))

        self.assertEqual(job.status, "done")
        self.assertAlmostEqual(job.progress, 1.0)

    def test_run_export_invalid_category_id_skipped(self):
        """Anotações com category_id inválido devem ser ignoradas, não gerar erro."""
        import asyncio
        from app.api.state import reset_state, create_session, frame_paths, frame_dims, annotation_store, next_ann_id
        from app.api.schemas import Annotation
        from app.core.exporter import ExportJob
        from app.api.state import create_export

        reset_state()
        session = create_session(
            mode="detection",
            data_path=Path(self._tmp),
            output_path=Path(self._tmp),
            classes=["car"],  # only id=0 valid
        )

        img_path = Path(self._tmp) / "frame_000.jpg"
        cv2.imwrite(str(img_path), np.zeros((50, 80, 3), dtype=np.uint8))
        frame_paths.append(img_path)
        frame_dims[0] = (80, 50)
        annotation_store[0] = [
            Annotation(id=1, image_id=0, category_id=99, bbox=[5.0, 5.0, 20.0, 15.0]),
        ]

        out_dir = Path(self._tmp) / "invalid_cat_out"
        job = create_export(ExportJob(
            destination=out_dir.parent,
            name=out_dir.name,
            formats=["yolo"],
            use_split=False,
        ))

        from app.api.routes.export import _run_export
        asyncio.run(_run_export(job.export_id))

        self.assertEqual(job.status, "done")
        # Image should be exported but label should be empty (invalid category skipped)
        label_files = list((out_dir / "labels" / "all").rglob("*.txt"))
        for lf in label_files:
            self.assertEqual(lf.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
