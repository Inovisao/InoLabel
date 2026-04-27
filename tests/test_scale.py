import unittest

from app.ui.layout.scale import apply_scale, compute_ui_scale


class ScaleTest(unittest.TestCase):
    def test_baseline_is_one(self):
        self.assertEqual(compute_ui_scale(1080, 96.0), 1.0)

    def test_small_screen_clamped_to_min(self):
        self.assertEqual(compute_ui_scale(768, 72.0), 1.0)

    def test_large_screen_clamped_to_max(self):
        self.assertEqual(compute_ui_scale(2160, 192.0), 1.35)

    def test_medium_screen_within_range(self):
        result = compute_ui_scale(1440, 120.0)
        self.assertGreater(result, 1.0)
        self.assertLess(result, 1.35)

    def test_scale_increases_with_resolution(self):
        low = compute_ui_scale(1080, 96.0)
        high = compute_ui_scale(1440, 120.0)
        self.assertGreater(high, low)

    def test_all_common_resolutions_in_range(self):
        for height in (768, 900, 1080, 1200, 1440, 1600, 2160):
            for dpi in (72.0, 96.0, 120.0, 144.0, 192.0):
                scale = compute_ui_scale(height, dpi)
                self.assertGreaterEqual(scale, 1.0)
                self.assertLessEqual(scale, 1.35)

    def test_apply_scale_scales_fonts_spacing_and_sizes(self):
        tokens = {
            "fonts": {"body": ("Helvetica", 12), "button": ("Helvetica", 12, "bold")},
            "spacing": {"md": 14},
            "sizes": {"sidebar_w": 320},
        }

        scaled = apply_scale(tokens, 1.25)

        self.assertEqual(scaled["fonts"]["body"], ("Helvetica", 15))
        self.assertEqual(scaled["fonts"]["button"], ("Helvetica", 15, "bold"))
        self.assertEqual(scaled["spacing"]["md"], 18)
        self.assertEqual(scaled["sizes"]["sidebar_w"], 400)


if __name__ == "__main__":
    unittest.main()
