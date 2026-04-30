import unittest

import numpy as np

from app.annotation_obb.geometry.obb_geometry import hbb_to_obb, obb_to_points, points_to_hbb, validate_obb


class OBBGeometryTest(unittest.TestCase):
    def test_hbb_to_obb_initializes_center_size_and_zero_angle(self):
        det = hbb_to_obb(441.0, 556.0, 535.0, 205.0, category_id=2)

        self.assertEqual(det.category_id, 2)
        self.assertAlmostEqual(det.cx, 708.5)
        self.assertAlmostEqual(det.cy, 658.5)
        self.assertAlmostEqual(det.width, 535.0)
        self.assertAlmostEqual(det.height, 205.0)
        self.assertAlmostEqual(det.angle, 0.0)

    def test_obb_to_points_without_rotation_matches_hbb_corners(self):
        points = obb_to_points(708.5, 658.5, 535.0, 205.0, 0.0)

        expected = np.array(
            [[441.0, 556.0], [976.0, 556.0], [976.0, 761.0], [441.0, 761.0]],
            dtype=np.float32,
        )
        np.testing.assert_allclose(points, expected, atol=1e-4)

    def test_points_to_hbb_returns_external_axis_aligned_box(self):
        points = obb_to_points(50.0, 50.0, 40.0, 20.0, 45.0)

        x, y, w, h = points_to_hbb(points)

        self.assertLess(x, 50.0)
        self.assertLess(y, 50.0)
        self.assertGreater(w, 40.0)
        self.assertGreater(h, 20.0)

    def test_validate_obb_rejects_tiny_boxes(self):
        self.assertFalse(validate_obb(hbb_to_obb(0, 0, 2, 10)))
        self.assertFalse(validate_obb(hbb_to_obb(0, 0, 10, 2)))
        self.assertTrue(validate_obb(hbb_to_obb(0, 0, 3, 3)))


if __name__ == "__main__":
    unittest.main()
