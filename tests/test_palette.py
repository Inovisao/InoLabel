import re
import unittest

from app.ui.theme.palette import CLASS_COLORS

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class PaletteTest(unittest.TestCase):
    def test_has_twelve_entries(self):
        self.assertEqual(len(CLASS_COLORS), 12)

    def test_all_are_valid_hex(self):
        for color in CLASS_COLORS:
            self.assertRegex(color, _HEX_RE, f"{color!r} is not a valid 6-digit hex color")

    def test_no_duplicates(self):
        self.assertEqual(len(CLASS_COLORS), len(set(CLASS_COLORS)))


if __name__ == "__main__":
    unittest.main()
