"""Testes das correcoes de caixas fora da resolucao da imagem (modo deteccao).

Cobre: recorte de bbox, descarte de caixas degeneradas, colisao de file_name entre
fontes, on_accept reaproveitando registro existente, corrida da inferencia em
background e sanitizacao nos exportadores COCO/YOLO.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

from app.annotation.core.augmentation.augmentation_service import _apply_entry
from app.annotation.core.augmentation.augmentation_types import AugEntry
from app.annotation.core.export.yolo_label_service import clip_coco_bbox, normalize_yolo_bbox
from app.annotation.detection.frame_pipeline import FramePipelineMixin
from app.annotation.detection.review_annotations import ReviewAnnotationsMixin
from app.annotation.detection.workflow_actions import WorkflowActionsMixin
from app.annotation.infrastructure.export.coco_exporter import convert_tracking_to_detection
from app.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from app.annotation.sources.source_helpers import SourceHelpersMixin
from app.geometry import clip_bbox, parse_frame_number_from_name
from app.models import Detection


def _det(x1, y1, x2, y2, source="manual"):
    return Detection(
        original_bbox=np.array([x1, y1, x2, y2], dtype=np.float32),
        warp_bbox=None,
        confidence=1.0,
        category_id=1,
        track_id=None,
        source=source,
    )


# ── Geometria ────────────────────────────────────────────────────────────────

class ClipBboxTest(unittest.TestCase):
    def test_full_image_box_keeps_full_size(self):
        np.testing.assert_array_equal(clip_bbox(-5, -5, 120, 90, 100, 80), [0, 0, 100, 80])

    def test_box_fully_outside_collapses_to_zero_area(self):
        x1, y1, x2, y2 = clip_bbox(150, 10, 200, 40, 100, 80)
        self.assertEqual(x2 - x1, 0)

    def test_parse_frame_number_accepts_source_qualified_name(self):
        self.assertEqual(parse_frame_number_from_name("cam2/video/video_frame_00042.jpg", "video"), 42)
        self.assertEqual(parse_frame_number_from_name("video_frame_00007.jpg", "video"), 7)


# ── Storage ──────────────────────────────────────────────────────────────────

class _Storage(CocoStorageMixin, ReviewAnnotationsMixin):
    def __init__(self, root: Path, video_files, frame_shape=(80, 100, 3)):
        self.data_root = root
        self.video_files = [Path(v) for v in video_files]
        self.output_images_dir = root / "out" / "images"
        self.images = []
        self.annotations = []
        self.image_id = 1
        self.annotation_id = 1
        self.frames_saved_in_current_video = 0
        self.tracking_enabled = False
        self.current_source_type = "video"
        self.current_source_image_path = None
        self.current_rectified_frame = None
        self.current_frame = np.zeros(frame_shape, dtype=np.uint8)
        self.frame_index = 1
        self.use_source(0)

    def use_source(self, index, frame_shape=None):
        self.video_path = self.video_files[index]
        self.video_name = self.video_path.stem
        if frame_shape is not None:
            self.current_frame = np.zeros(frame_shape, dtype=np.uint8)


class StoreAnnotationsBoundsTest(unittest.TestCase):
    def test_boxes_are_clipped_and_degenerate_ones_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = _Storage(root, [root / "video.mp4"])
            dets = [_det(90, 70, 130, 120), _det(150, 10, 200, 40), _det(10, 10, 30, 30)]

            image_id, _ = storage.store_annotations(dets)

            anns = [a for a in storage.annotations if a["image_id"] == image_id]
            self.assertEqual(len(anns), 2)
            for ann in anns:
                x, y, w, h = ann["bbox"]
                self.assertGreater(w, 0)
                self.assertGreater(h, 0)
                self.assertLessEqual(x + w, 100)
                self.assertLessEqual(y + h, 80)
                self.assertAlmostEqual(ann["area"], w * h)
            self.assertEqual(anns[0]["bbox"], [90.0, 70.0, 10.0, 10.0])


class SourceFileNameCollisionTest(unittest.TestCase):
    def _two_cams(self, root):
        return [root / "cam1" / "video.mp4", root / "cam2" / "video.mp4"]

    def test_second_source_with_same_stem_gets_qualified_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = _Storage(root, self._two_cams(root), frame_shape=(80, 100, 3))
            _, name_cam1 = storage.store_annotations([_det(10, 10, 90, 70)])

            storage.use_source(1, frame_shape=(40, 50, 3))
            name_cam2 = storage.current_frame_file_name()
            self.assertEqual(name_cam1, "video_frame_00001.jpg")
            self.assertEqual(name_cam2, "cam2/video/video_frame_00001.jpg")
            self.assertIsNone(storage.find_image_record_by_file_name(name_cam2))

            _, saved_cam2 = storage.store_annotations([_det(5, 5, 45, 35)])
            self.assertEqual(saved_cam2, name_cam2)

            # O JPG da cam1 continua com a resolucao da cam1 e bate com o registro.
            cam1_img = cv2.imread(str(storage.output_images_dir / name_cam1))
            record_cam1 = storage.find_image_record_by_file_name(name_cam1)
            self.assertEqual(cam1_img.shape[:2], (record_cam1["height"], record_cam1["width"]))
            self.assertEqual(cam1_img.shape[:2], (80, 100))
            self.assertEqual(len(storage.images), 2)

    def test_qualified_name_is_stable_for_resume_and_autosave(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = _Storage(root, self._two_cams(root))
            storage.store_annotations([])
            storage.use_source(1)
            storage.store_annotations([])

            storage.use_source(0)
            self.assertEqual(storage.existing_record_for_current_frame()["id"], 1)
            storage.use_source(1)
            self.assertEqual(storage.existing_record_for_current_frame()["id"], 2)

    def test_record_from_moved_dataset_is_treated_as_current_source(self):
        """Dataset movido de pasta: o registro antigo nao pode virar 'de outra fonte'."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = _Storage(root, [root / "cam1" / "a.mp4", root / "cam2" / "b.mp4"])
            storage.video_name = "a"
            storage.images = [{
                "id": 1, "file_name": "a_frame_00001.jpg", "width": 100, "height": 80,
                "video": "/caminho/antigo/cam1/a.mp4",
            }]
            storage._invalidate_storage_cache()

            self.assertEqual(storage.current_frame_file_name(), "a_frame_00001.jpg")
            self.assertEqual(storage.existing_record_for_current_frame()["id"], 1)

    def test_single_source_never_qualifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = _Storage(root, [root / "cam1" / "video.mp4"])
            storage.images = [{"id": 1, "file_name": "video_frame_00001.jpg", "video": "/outro/video.mp4"}]
            storage._invalidate_storage_cache()
            self.assertEqual(storage.current_frame_file_name(), "video_frame_00001.jpg")


class ResumeCursorQualifiedNameTest(unittest.TestCase):
    def test_cursor_matches_source_qualified_file_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_paths = [Path("/fora/do/root") / f"img_{i}.jpg" for i in range(3)]

            class DummySource(SourceHelpersMixin):
                def __init__(self):
                    self.data_root = root
                    self.video_path = root / "lista_b.txt"
                    self.current_image_paths = image_paths
                    self.frame_index = 0
                    self.annotation_state = {"last_active_file_name": "lista_b/img_2.jpg"}

            self.assertEqual(DummySource()._find_resume_image_cursor(), 2)


# ── on_accept ────────────────────────────────────────────────────────────────

class _AcceptWorkflow(WorkflowActionsMixin):
    def __init__(self, existing):
        self.current_frame = np.zeros((8, 8, 3), dtype=np.uint8)
        self.current_detections = []
        self.manual_detections = []
        self.review_idx = None
        self.saved_records = []
        self.store_calls = []
        self._existing = existing

    def existing_record_for_current_frame(self):
        return self._existing

    def store_annotations(self, detections, existing_image_id=None, existing_file_name=None):
        self.store_calls.append((existing_image_id, existing_file_name))
        return existing_image_id or 99, existing_file_name or "novo.jpg"

    def write_annotations(self, *, blocking=False):
        pass

    def remember_saved_record(self, detections, image_id, file_name):
        self.saved_records.append((image_id, file_name))

    def load_next_frame(self):
        pass


class AcceptReusesExistingRecordTest(unittest.TestCase):
    def test_accept_on_already_saved_frame_updates_same_record(self):
        workflow = _AcceptWorkflow({"id": 5, "file_name": "lote/a.jpg"})
        workflow.on_accept()
        self.assertEqual(workflow.store_calls, [(5, "lote/a.jpg")])
        self.assertEqual(workflow.saved_records, [(5, "lote/a.jpg")])

    def test_accept_on_new_frame_creates_record(self):
        workflow = _AcceptWorkflow(None)
        workflow.on_accept()
        self.assertEqual(workflow.store_calls, [(None, None)])


# ── Corrida da inferencia em background ──────────────────────────────────────

class _ImmediateThread:
    def __init__(self, target, daemon=None):
        self._target = target

    def start(self):
        self._target()


class _Window:
    def __init__(self):
        self.callbacks = []

    def after(self, _ms, callback):
        self.callbacks.append(callback)


class _Pipeline(FramePipelineMixin, CocoStorageMixin, ReviewAnnotationsMixin):
    def __init__(self):
        self.window = _Window()
        self.frame_index = 0
        self.drawing_rect_id = None
        self.max_undo_states = 10
        self.review_idx = None
        self.current_detections = []
        self.manual_detections = []
        self.images = []
        self.annotations = []
        self.model_output = []

    def warp_frame(self, frame):
        return None

    def run_model(self, frame):
        return list(self.model_output)

    def update_annotation_button(self):
        pass

    update_remove_button = update_selection_button = update_annotation_button

    def update_display(self, *, refresh_status=False):
        pass


@mock.patch("app.annotation.detection.frame_pipeline.threading.Thread", _ImmediateThread)
class InferenceRaceTest(unittest.TestCase):
    def test_inference_applies_to_its_own_frame(self):
        pipe = _Pipeline()
        pipe.model_output = [_det(1, 1, 5, 5, source="model")]
        pipe.process_current_frame(np.zeros((10, 10, 3), dtype=np.uint8), render=False)
        pipe.window.callbacks.pop()()
        self.assertEqual(len(pipe.current_detections), 1)

    def test_stale_inference_with_same_frame_index_is_ignored(self):
        """Fonte nova reinicia frame_index: o resultado da fonte anterior nao pode vazar."""
        pipe = _Pipeline()
        pipe.model_output = [_det(100, 100, 400, 300, source="model")]
        pipe.process_current_frame(np.zeros((480, 640, 3), dtype=np.uint8), render=False)
        stale_apply = pipe.window.callbacks.pop()

        pipe.frame_index = 0  # proxima fonte comeca do zero de novo
        pipe.model_output = []
        pipe.process_current_frame(np.zeros((40, 50, 3), dtype=np.uint8), render=False)
        pipe.window.callbacks.pop()()
        stale_apply()

        self.assertEqual(pipe.current_detections, [])

    def test_restored_annotations_are_not_overwritten_by_inference(self):
        pipe = _Pipeline()
        pipe.images = [{"id": 1, "file_name": "f.jpg"}]
        pipe.annotations = [{
            "id": 1, "image_id": 1, "category_id": 2, "bbox": [1, 1, 3, 3], "source": "model",
        }]
        pipe.current_frame_file_name = lambda: "f.jpg"
        pipe.model_output = [_det(0, 0, 9, 9, source="model"), _det(2, 2, 4, 4, source="model")]

        pipe.process_current_frame(np.zeros((10, 10, 3), dtype=np.uint8), render=False)
        pipe.restore_saved_annotations_for_current_frame()
        pipe.window.callbacks.pop()()

        self.assertEqual(len(pipe.current_detections), 1)
        self.assertEqual(pipe.current_detections[0].category_id, 2)


# ── Exportadores ─────────────────────────────────────────────────────────────

class ExportSanitizationTest(unittest.TestCase):
    def _payload(self, bboxes):
        return {
            "images": [{"id": 1, "file_name": "a.jpg", "width": 100, "height": 80}],
            "annotations": [
                {"id": i, "image_id": 1, "category_id": 1, "bbox": bbox, "area": 1.0}
                for i, bbox in enumerate(bboxes, 1)
            ],
            "categories": [{"id": 1, "name": "obj"}],
        }

    def test_coco_export_clips_and_drops_out_of_bounds_boxes(self):
        out = convert_tracking_to_detection(self._payload([[90, 70, 30, 30], [200, 10, 5, 5], [10, 10, 5, 5]]))
        bboxes = [ann["bbox"] for ann in out["annotations"]]
        self.assertEqual(bboxes, [[90.0, 70.0, 10.0, 10.0], [10.0, 10.0, 5.0, 5.0]])
        self.assertEqual(out["annotations"][0]["area"], 100.0)
        self.assertEqual(out["annotations"][1]["area"], 1.0)  # caixa valida preserva a area original

    def test_yolo_normalize_clips_small_overflow_instead_of_dropping(self):
        values = normalize_yolo_bbox([50, 40, 50.0001, 40], 100, 80)
        self.assertIsNotNone(values)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in values))

    def test_clip_coco_bbox_rejects_box_outside_image(self):
        self.assertIsNone(clip_coco_bbox([120, 10, 5, 5], 100, 80))
        self.assertIsNone(clip_coco_bbox([10, 10, 0, 5], 100, 80))


class ShearAugmentationTest(unittest.TestCase):
    def test_shear_keeps_image_center_fixed_on_non_square_image(self):
        image = np.zeros((100, 300, 3), dtype=np.uint8)
        box = [0, 0.5, 0.5, 0.1, 0.1]
        entry = AugEntry(key="shear", enabled=True, params={"prob": 1.0, "max_degrees": 20.0})
        _, boxes = _apply_entry(image, [box], entry, np.random.default_rng(0))
        self.assertAlmostEqual(boxes[0][1], 0.5, places=3)


if __name__ == "__main__":
    unittest.main()
