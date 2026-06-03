import unittest

import numpy as np

from tracker import matching


class TrackerMatchingFallbackTest(unittest.TestCase):
    def test_numpy_bbox_overlaps_matches_cython_bbox_shape_and_values(self):
        boxes = np.array([[0, 0, 9, 9], [10, 10, 19, 19]], dtype=float)
        query_boxes = np.array([[0, 0, 9, 9], [5, 5, 14, 14], [30, 30, 39, 39]], dtype=float)

        overlaps = matching._bbox_overlaps_numpy(boxes, query_boxes)

        self.assertEqual(overlaps.shape, (2, 3))
        self.assertAlmostEqual(overlaps[0, 0], 1.0)
        self.assertAlmostEqual(overlaps[0, 1], 25.0 / 175.0)
        self.assertAlmostEqual(overlaps[0, 2], 0.0)
        self.assertAlmostEqual(overlaps[1, 1], 25.0 / 175.0)

    def test_scipy_linear_assignment_respects_threshold(self):
        cost_matrix = np.array(
            [
                [0.1, 0.9, 0.8],
                [0.7, 0.2, 0.8],
                [0.8, 0.9, 0.6],
            ],
            dtype=float,
        )

        matches, unmatched_rows, unmatched_cols = matching._linear_assignment_scipy(cost_matrix, thresh=0.5)

        self.assertEqual(matches.tolist(), [[0, 0], [1, 1]])
        self.assertEqual(unmatched_rows, (2,))
        self.assertEqual(unmatched_cols, (2,))


if __name__ == "__main__":
    unittest.main()
