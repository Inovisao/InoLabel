"""Tests covering CocoStorageMixin lookup and rebuild methods.

These tests lock in the current behaviour before optimising the linear
scans to O(1) index lookups, so we can confirm the optimised versions
produce identical results.
"""

import unittest

import numpy as np

from app.annotation.infrastructure.persistence.coco_storage import CocoStorageMixin
from app.annotation.detection.review_annotations import ReviewAnnotationsMixin
from app.models import Detection


# ── Minimal stub that mixes in both classes ────────────────────────────────────

class _Stub(CocoStorageMixin, ReviewAnnotationsMixin):
    def __init__(self, images, annotations):
        self.images = list(images)
        self.annotations = list(annotations)
        self.tracking_enabled = False


def _make_ann(ann_id, image_id, category_id, bbox=(0, 0, 10, 10), source="manual"):
    return {
        "id": ann_id,
        "image_id": image_id,
        "category_id": category_id,
        "bbox": list(bbox),
        "score": 1.0,
        "source": source,
    }


def _make_img(img_id, file_name, width=100, height=100):
    return {"id": img_id, "file_name": file_name, "width": width, "height": height}


# ── find_image_record_by_file_name ────────────────────────────────────────────

class FindImageByFileNameTest(unittest.TestCase):

    def setUp(self):
        self.stub = _Stub(
            images=[
                _make_img(1, "a/img_001.jpg"),
                _make_img(2, "a/img_002.jpg"),
                _make_img(3, "b/img_003.jpg"),
            ],
            annotations=[],
        )

    def test_returns_correct_record(self):
        result = self.stub.find_image_record_by_file_name("a/img_002.jpg")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2)

    def test_returns_none_for_missing(self):
        result = self.stub.find_image_record_by_file_name("nonexistent.jpg")
        self.assertIsNone(result)

    def test_returns_none_for_empty_list(self):
        stub = _Stub(images=[], annotations=[])
        self.assertIsNone(stub.find_image_record_by_file_name("img.jpg"))

    def test_matches_exact_file_name(self):
        # Should not match on partial names
        self.assertIsNone(self.stub.find_image_record_by_file_name("img_001.jpg"))
        self.assertIsNotNone(self.stub.find_image_record_by_file_name("a/img_001.jpg"))

    def test_returns_first_match_on_duplicate_names(self):
        stub = _Stub(
            images=[_make_img(1, "dup.jpg"), _make_img(2, "dup.jpg")],
            annotations=[],
        )
        result = stub.find_image_record_by_file_name("dup.jpg")
        self.assertEqual(result["id"], 1)

    def test_consistent_after_images_mutated(self):
        self.stub.images.append(_make_img(4, "new.jpg"))
        result = self.stub.find_image_record_by_file_name("new.jpg")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 4)


# ── rebuild_detections_from_annotations ──────────────────────────────────────

class RebuildDetectionsTest(unittest.TestCase):

    def setUp(self):
        self.stub = _Stub(
            images=[_make_img(10, "frame.jpg", 200, 200)],
            annotations=[
                _make_ann(1, 10, 1, bbox=(5, 5, 20, 20), source="model"),
                _make_ann(2, 10, 2, bbox=(30, 30, 50, 50), source="manual"),
                _make_ann(3, 99, 1, bbox=(0, 0, 10, 10)),  # different image_id
            ],
        )

    def test_returns_only_detections_for_given_image_id(self):
        dets = self.stub.rebuild_detections_from_annotations(10, 200, 200)
        self.assertEqual(len(dets), 2)

    def test_returns_empty_for_unknown_image_id(self):
        dets = self.stub.rebuild_detections_from_annotations(999, 200, 200)
        self.assertEqual(dets, [])

    def test_detection_fields_are_correct(self):
        dets = self.stub.rebuild_detections_from_annotations(10, 200, 200)
        sources = {d.source for d in dets}
        cats = {d.category_id for d in dets}
        self.assertEqual(sources, {"model", "manual"})
        self.assertEqual(cats, {1, 2})

    def test_bbox_is_clipped_to_frame_dimensions(self):
        stub = _Stub(
            images=[],
            annotations=[_make_ann(1, 5, 1, bbox=(0, 0, 300, 300))],
        )
        dets = stub.rebuild_detections_from_annotations(5, 100, 100)
        self.assertEqual(len(dets), 1)
        x1, y1, x2, y2 = dets[0].original_bbox
        self.assertLessEqual(x2, 100)
        self.assertLessEqual(y2, 100)

    def test_returns_empty_for_no_annotations(self):
        stub = _Stub(images=[], annotations=[])
        dets = stub.rebuild_detections_from_annotations(1, 100, 100)
        self.assertEqual(dets, [])

    def test_track_id_preserved(self):
        stub = _Stub(
            images=[],
            annotations=[{
                "id": 1, "image_id": 7, "category_id": 1,
                "bbox": [0, 0, 10, 10], "score": 0.9,
                "source": "model", "track_id": 42,
            }],
        )
        dets = stub.rebuild_detections_from_annotations(7, 200, 200)
        self.assertEqual(dets[0].track_id, 42)

    def test_consistent_after_annotations_mutated(self):
        self.stub.annotations.append(_make_ann(4, 10, 3, source="manual"))
        dets = self.stub.rebuild_detections_from_annotations(10, 200, 200)
        self.assertEqual(len(dets), 3)

    def test_large_annotation_list_returns_correct_subset(self):
        images = [_make_img(i, f"img_{i}.jpg") for i in range(500)]
        annotations = [_make_ann(i, i % 10, 1) for i in range(5000)]
        stub = _Stub(images=images, annotations=annotations)
        dets = stub.rebuild_detections_from_annotations(3, 200, 200)
        expected = sum(1 for a in annotations if a["image_id"] == 3)
        self.assertEqual(len(dets), expected)


# ── restore_saved_annotations_for_current_frame ──────────────────────────────

class RestoreSavedAnnotationsTest(unittest.TestCase):

    def test_restores_model_and_manual_detections_separately(self):
        stub = _Stub(
            images=[_make_img(1, "frame.jpg", 100, 100)],
            annotations=[
                _make_ann(1, 1, 1, source="model"),
                _make_ann(2, 1, 2, source="manual"),
            ],
        )
        stub.current_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        stub.current_detections = []
        stub.manual_detections = []
        stub.selected_detection = None

        # Patch current_frame_file_name to return "frame.jpg"
        stub.current_frame_file_name = lambda: "frame.jpg"

        stub.restore_saved_annotations_for_current_frame()

        self.assertEqual(len(stub.current_detections), 1)
        self.assertEqual(stub.current_detections[0].source, "model")
        self.assertEqual(len(stub.manual_detections), 1)
        self.assertEqual(stub.manual_detections[0].source, "manual")

    def test_does_nothing_when_file_name_not_found(self):
        stub = _Stub(
            images=[_make_img(1, "other.jpg", 100, 100)],
            annotations=[_make_ann(1, 1, 1)],
        )
        stub.current_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        stub.current_detections = []
        stub.manual_detections = []
        stub.selected_detection = None
        stub.current_frame_file_name = lambda: "missing.jpg"

        stub.restore_saved_annotations_for_current_frame()

        self.assertEqual(stub.current_detections, [])
        self.assertEqual(stub.manual_detections, [])


if __name__ == "__main__":
    unittest.main()
