import unittest

from app.ui.theme import build_scaled_theme


class ThemeTest(unittest.TestCase):
    def test_scaled_fonts_are_tuples(self):
        theme = build_scaled_theme(scale=1.2)

        for font in theme["fonts"].values():
            self.assertIsInstance(font, tuple)
            self.assertIsInstance(font[0], str)
            self.assertIsInstance(font[1], int)
            self.assertGreater(font[1], 0)

    def test_scaled_spacing_and_sizes_are_positive_ints(self):
        theme = build_scaled_theme(scale=1.2)

        for bucket in ("spacing", "sizes"):
            for value in theme[bucket].values():
                self.assertIsInstance(value, int)
                self.assertGreater(value, 0)

    def test_colors_are_not_scaled(self):
        theme = build_scaled_theme(scale=1.3)

        self.assertEqual(theme["colors"]["primary"], "#1560BD")


if __name__ == "__main__":
    unittest.main()
