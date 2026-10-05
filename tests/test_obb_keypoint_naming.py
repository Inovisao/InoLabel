"""A1 — OBB e keypoint: nomes de arquivo unicos entre fontes e on_accept sem duplicar registro.

Mesmas garantias ja cobertas para a deteccao em tests/test_bbox_bounds.py.
"""

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from app.annotation_keypoint.detection.workflow_actions import KPWorkflowActionsMixin
from app.annotation_keypoint.infrastructure.persistence.coco_storage import KPCocoStorageMixin
from app.annotation_keypoint.sources.source_helpers import KPSourceHelpersMixin
from app.annotation_obb.detection.workflow_actions import OBBWorkflowActionsMixin
from app.annotation_obb.infrastructure.persistence.obb_coco_storage import OBBCocoStorageMixin
from app.annotation_obb.sources.source_helpers import OBBSourceHelpersMixin

STORAGES = (OBBCocoStorageMixin, KPCocoStorageMixin)


def _make_storage(mixin, root: Path, video_files, frame_shape=(80, 100, 3)):
    storage = type("Storage", (mixin,), {})()
    storage.data_root = root
    storage.video_files = [Path(v) for v in video_files]
    storage.output_images_dir = root / "out" / "images"
    storage.images = []
    storage.annotations = []
    storage.image_id = 1
    storage.annotation_id = 1
    storage.frames_saved_in_current_video = 0
    storage.current_source_type = "video"
    storage.current_source_image_path = None
    storage.current_rectified_frame = None
    storage.current_frame = np.zeros(frame_shape, dtype=np.uint8)
    storage.frame_index = 1
    use_source(storage, 0)
    return storage


def use_source(storage, index, frame_shape=None):
    storage.video_path = storage.video_files[index]
    storage.video_name = storage.video_path.stem
    if frame_shape is not None:
        storage.current_frame = np.zeros(frame_shape, dtype=np.uint8)


class SourceCollisionTest(unittest.TestCase):
    def test_same_stem_in_two_folders_never_shares_a_file(self):
        for mixin in STORAGES:
            with self.subTest(mode=mixin.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                cams = [root / "cam1" / "video.mp4", root / "cam2" / "video.mp4"]
                storage = _make_storage(mixin, root, cams, frame_shape=(80, 100, 3))
                _, name_cam1 = storage.store_annotations([])

                use_source(storage, 1, frame_shape=(40, 50, 3))
                _, name_cam2 = storage.store_annotations([])

                self.assertEqual(name_cam1, "video_frame_00001.jpg")
                self.assertEqual(name_cam2, "cam2/video/video_frame_00001.jpg")
                cam1_img = cv2.imread(str(storage.output_images_dir / name_cam1))
                self.assertEqual(cam1_img.shape[:2], (80, 100))  # nao foi sobrescrito
                self.assertEqual(len(storage.images), 2)

    def test_qualified_name_is_found_again_on_resume(self):
        for mixin in STORAGES:
            with self.subTest(mode=mixin.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                storage = _make_storage(mixin, root, [root / "a" / "v.mp4", root / "b" / "v.mp4"])
                storage.store_annotations([])
                use_source(storage, 1)
                storage.store_annotations([])

                use_source(storage, 0)
                self.assertEqual(storage.existing_record_for_current_frame()["id"], 1)
                use_source(storage, 1)
                self.assertEqual(storage.existing_record_for_current_frame()["id"], 2)

    def test_single_source_keeps_legacy_names(self):
        for mixin in STORAGES:
            with self.subTest(mode=mixin.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                storage = _make_storage(mixin, root, [root / "cam1" / "video.mp4"])
                self.assertEqual(storage.current_frame_file_name(), "video_frame_00001.jpg")


class ResumeCursorTest(unittest.TestCase):
    def test_cursor_matches_qualified_name(self):
        for mixin in (OBBSourceHelpersMixin, KPSourceHelpersMixin):
            with self.subTest(mode=mixin.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = type("Source", (mixin,), {})()
                source.data_root = root
                source.video_path = root / "lista_b.txt"
                source.current_image_paths = [Path("/fora") / f"img_{i}.jpg" for i in range(3)]
                source.frame_index = 0
                source.annotation_state = {"last_active_file_name": "lista_b/img_2.jpg"}
                self.assertEqual(source._find_resume_image_cursor(), 2)


def _accept_workflow(mixin, existing):
    class Workflow(mixin):
        def __init__(self):
            self.current_frame = np.zeros((8, 8, 3), dtype=np.uint8)
            self.review_idx = None
            self.saved_records = []
            self.store_calls = []

        def detections_to_save(self):
            return []

        def existing_record_for_current_frame(self):
            return existing

        def store_annotations(self, detections, existing_image_id=None, existing_file_name=None):
            self.store_calls.append((existing_image_id, existing_file_name))
            return existing_image_id or 99, existing_file_name or "novo.jpg"

        def write_annotations(self, *, blocking=False):
            pass

        def remember_saved_record(self, detections, image_id, file_name):
            self.saved_records.append((image_id, file_name))

        def load_next_frame(self):
            pass

    return Workflow()


class AcceptReusesRecordTest(unittest.TestCase):
    def test_accept_on_saved_frame_updates_same_record(self):
        for mixin in (OBBWorkflowActionsMixin, KPWorkflowActionsMixin):
            with self.subTest(mode=mixin.__name__):
                workflow = _accept_workflow(mixin, {"id": 5, "file_name": "lote/a.jpg"})
                workflow.on_accept()
                self.assertEqual(workflow.store_calls, [(5, "lote/a.jpg")])
                self.assertEqual(workflow.saved_records, [(5, "lote/a.jpg")])

    def test_accept_on_new_frame_creates_record(self):
        for mixin in (OBBWorkflowActionsMixin, KPWorkflowActionsMixin):
            with self.subTest(mode=mixin.__name__):
                workflow = _accept_workflow(mixin, None)
                workflow.on_accept()
                self.assertEqual(workflow.store_calls, [(None, None)])


if __name__ == "__main__":
    unittest.main()
