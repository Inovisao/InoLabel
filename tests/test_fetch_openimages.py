import csv
import tempfile
import unittest
from pathlib import Path

from utils.fetch_openimages import (
    CLASS_LABELS,
    HUMAN_FACE,
    Box,
    Candidate,
    _write_manifest,
    select_candidates,
)

HAT = "/m/02dl1y"
HAT_LABELS = set(CLASS_LABELS["hat"])


def _row(image_id, label, x1, x2, y1, y2, group="0", depiction="0"):
    return {
        "ImageID": image_id,
        "LabelName": label,
        "XMin": str(x1),
        "XMax": str(x2),
        "YMin": str(y1),
        "YMax": str(y2),
        "IsGroupOf": group,
        "IsDepiction": depiction,
    }


class SelectCandidatesTest(unittest.TestCase):
    def _select(self, rows, min_face_area=0.06):
        return [c.image_id for c in select_candidates(rows, "validation", HAT_LABELS, min_face_area)]

    def test_accepts_single_large_face_with_hat_on_top(self):
        rows = [
            _row("selfie", HUMAN_FACE, 0.3, 0.7, 0.3, 0.8),
            _row("selfie", HAT, 0.25, 0.75, 0.1, 0.35),
        ]
        self.assertEqual(self._select(rows), ["selfie"])

    def test_rejects_images_with_more_than_one_face(self):
        rows = [
            _row("group", HUMAN_FACE, 0.1, 0.4, 0.3, 0.8),
            _row("group", HUMAN_FACE, 0.5, 0.9, 0.3, 0.8),
            _row("group", HAT, 0.1, 0.4, 0.1, 0.3),
        ]
        self.assertEqual(self._select(rows), [])

    def test_rejects_small_face(self):
        rows = [
            _row("far", HUMAN_FACE, 0.45, 0.55, 0.45, 0.55),  # 1% of the image
            _row("far", HAT, 0.45, 0.55, 0.40, 0.46),
        ]
        self.assertEqual(self._select(rows), [])

    def test_rejects_hat_far_from_the_face(self):
        rows = [
            _row("shop", HUMAN_FACE, 0.0, 0.4, 0.0, 0.5),
            _row("shop", HAT, 0.8, 1.0, 0.8, 1.0),
        ]
        self.assertEqual(self._select(rows), [])

    def test_rejects_group_or_depiction_boxes(self):
        rows = [
            _row("drawing", HUMAN_FACE, 0.3, 0.7, 0.3, 0.8, depiction="1"),
            _row("drawing", HAT, 0.25, 0.75, 0.1, 0.35),
            _row("pile", HUMAN_FACE, 0.3, 0.7, 0.3, 0.8),
            _row("pile", HAT, 0.25, 0.75, 0.1, 0.35, group="1"),
        ]
        self.assertEqual(self._select(rows), [])

    def test_ignores_images_without_target_class(self):
        rows = [_row("plain", HUMAN_FACE, 0.3, 0.7, 0.3, 0.8)]
        self.assertEqual(self._select(rows), [])


class ManifestTest(unittest.TestCase):
    def test_manifest_keeps_attribution_and_boxes(self):
        candidate = Candidate(
            image_id="abc",
            split="test",
            target_boxes=[Box(HAT, 0.1, 0.5, 0.2, 0.4)],
            face=Box(HUMAN_FACE, 0.1, 0.5, 0.3, 0.9),
            metadata={
                "License": "https://creativecommons.org/licenses/by/2.0/",
                "Author": "Fulano",
                "AuthorProfileURL": "https://www.flickr.com/people/x/",
                "OriginalLandingURL": "https://www.flickr.com/photos/x/1",
            },
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "candidates.csv"
            _write_manifest(path, "hat", [candidate])
            with path.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["file"], "abc.jpg")
        self.assertEqual(rows[0]["openimages_labels"], "Hat")
        self.assertEqual(rows[0]["boxes_xyxy_normalized"], "0.1000,0.2000,0.5000,0.4000")
        self.assertEqual(rows[0]["author"], "Fulano")
        self.assertEqual(rows[0]["landing_url"], "https://www.flickr.com/photos/x/1")


if __name__ == "__main__":
    unittest.main()
