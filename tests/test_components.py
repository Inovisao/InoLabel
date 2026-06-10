import tkinter as tk
import unittest


class TkTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tkinter indisponivel neste ambiente: {exc}")
        self.root.withdraw()

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()


class MakeBtnTest(TkTestCase):
    def setUp(self):
        super().setUp()
        from app.ui.components import make_btn
        self.make_btn = make_btn

    def test_returns_tk_button(self):
        btn = self.make_btn(self.root, "Test", lambda: None)
        self.assertIsInstance(btn, tk.Button)

    def test_variants_do_not_raise(self):
        for variant in ("primary", "danger", "neutral", "accent", "ghost"):
            btn = self.make_btn(self.root, variant, lambda: None, variant=variant)
            self.assertIsInstance(btn, tk.Button)

    def test_sizes_do_not_raise(self):
        for size in ("md", "sm"):
            btn = self.make_btn(self.root, size, lambda: None, size=size)
            self.assertIsInstance(btn, tk.Button)

    def test_disabled_state(self):
        btn = self.make_btn(self.root, "Disabled", lambda: None, state=tk.DISABLED)
        self.assertEqual(str(btn["state"]), "disabled")


class CardTest(TkTestCase):
    def test_card_is_frame(self):
        from app.ui.components.card import Card
        card = Card(self.root)
        self.assertIsInstance(card, tk.Frame)


class MakeEntryTest(TkTestCase):
    def test_returns_tk_entry(self):
        from app.ui.components import make_entry
        var = tk.StringVar()
        entry = make_entry(self.root, var)
        self.assertIsInstance(entry, tk.Entry)

    def test_textvariable_bound(self):
        from app.ui.components import make_entry
        var = tk.StringVar(value="hello")
        entry = make_entry(self.root, var)
        self.assertEqual(entry.get(), "hello")


class MakeBadgeTest(TkTestCase):
    def test_returns_tk_label(self):
        from app.ui.components import make_badge
        badge = make_badge(self.root, "Tracking", color="#1560BD")
        self.assertIsInstance(badge, tk.Label)


if __name__ == "__main__":
    unittest.main()
