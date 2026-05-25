import unittest


class ThemeCompatTest(unittest.TestCase):
    """Legacy import path from app.ui.theme must still work after restructuring."""

    def test_colors_importable(self):
        from app.ui.theme import COLORS  # noqa: F401
        self.assertIsInstance(COLORS, dict)
        self.assertIn("primary", COLORS)

    def test_fonts_importable(self):
        from app.ui.theme import FONTS  # noqa: F401
        self.assertIsInstance(FONTS, dict)

    def test_spacing_importable(self):
        from app.ui.theme import SPACING  # noqa: F401
        self.assertIsInstance(SPACING, dict)

    def test_sizes_importable(self):
        from app.ui.theme import SIZES  # noqa: F401
        self.assertIsInstance(SIZES, dict)

    def test_class_colors_importable(self):
        from app.ui.theme import CLASS_COLORS  # noqa: F401
        self.assertIsInstance(CLASS_COLORS, list)
        self.assertGreater(len(CLASS_COLORS), 0)

    def test_build_scaled_theme_importable(self):
        from app.ui.theme import build_scaled_theme  # noqa: F401
        theme = build_scaled_theme(scale=1.0)
        self.assertIn("colors", theme)
        self.assertEqual(theme["colors"]["primary"], "#1560BD")


if __name__ == "__main__":
    unittest.main()
