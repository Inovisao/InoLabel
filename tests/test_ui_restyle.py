"""Testes da reestilizacao da tela de anotacao: contraste, marca, botoes, toggles e sidebar."""

import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.annotation.presentation.labels import KEY_SEPARATOR, SIDEBAR_LABELS, ButtonLabel
from app.annotation.presentation.panels.sidebar_panel import SidebarPanelMixin
from app.annotation.presentation.panels.topbar_panel import TopbarPanelMixin
from app.annotation.ui.ui_controls import UIControlsMixin
from app.ui.components import ToggleButton, make_btn, make_toggle
from app.ui.components.badge import readable_fg
from app.ui.components.brand import load_brand_image, make_brand_mark, set_window_icon
from app.ui.theme.contrast import contrast_ratio
from app.ui.theme.tokens import COLORS, TEXT_CONTRAST_PAIRS


class TkTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def hover(self, widget, enter=True):
        # Tk so entrega <Enter>/<Leave> a widgets mapeados: mostra a janela fora da tela.
        if not widget.winfo_ismapped():
            widget.pack()
            self.root.geometry("+-3000+-3000")
            self.root.deiconify()
            self.root.update()
        widget.event_generate("<Enter>" if enter else "<Leave>")
        self.root.update_idletasks()


# ── Contraste ────────────────────────────────────────────────────────────────

class ContrastTest(unittest.TestCase):
    def test_reference_values(self):
        self.assertAlmostEqual(contrast_ratio("#FFFFFF", "#000000"), 21.0, places=2)
        self.assertAlmostEqual(contrast_ratio("#1560BD", "#1560BD"), 1.0)

    def test_every_declared_text_pair_meets_wcag_aa(self):
        for fg, bg in TEXT_CONTRAST_PAIRS:
            with self.subTest(fg=fg, bg=bg):
                self.assertGreaterEqual(contrast_ratio(COLORS[fg], COLORS[bg]), 4.5)

    def test_white_on_brand_orange_is_what_we_avoid(self):
        self.assertLess(contrast_ratio("#FFFFFF", COLORS["accent"]), 4.5)

    def test_readable_fg_picks_highest_contrast(self):
        self.assertEqual(readable_fg(COLORS["primary"]), COLORS["fg_light"])
        self.assertEqual(readable_fg(COLORS["accent"]), COLORS["text"])
        self.assertEqual(readable_fg("#FFD60A"), COLORS["text"])  # classe amarela


# ── Marca ────────────────────────────────────────────────────────────────────

class BrandImageTest(unittest.TestCase):
    def setUp(self):
        load_brand_image.cache_clear()

    def test_crops_transparent_border_before_resizing(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logo.png"
            img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
            img.paste((21, 96, 189, 255), (150, 50, 250, 150))  # desenho 100x100 no meio
            img.save(path)

            logo = load_brand_image(20, str(path))

        self.assertEqual(logo.size, (20, 20))

    def test_missing_file_returns_none(self):
        self.assertIsNone(load_brand_image(20, "/nao/existe/logo.png"))

    def test_result_is_cached(self):
        self.assertIs(load_brand_image(24), load_brand_image(24))


class BrandMarkTest(TkTestCase):
    def test_brand_mark_shows_logo_and_name(self):
        mark = make_brand_mark(self.root, height=24)
        texts = [w.cget("text") for w in mark.winfo_children() if isinstance(w, tk.Label)]
        self.assertIn("InoLabel", texts)
        self.assertTrue(hasattr(mark, "logo_label"))

    def test_window_icon_is_set(self):
        self.assertTrue(set_window_icon(self.root))


# ── Botoes ───────────────────────────────────────────────────────────────────

class ButtonHoverTest(TkTestCase):
    def test_leave_restores_current_bg_not_creation_bg(self):
        btn = make_btn(self.root, "x", variant="neutral")
        btn.configure(bg="#123456")  # alguem reestilizou depois de criar
        self.hover(btn, True)
        self.assertNotEqual(btn.cget("bg"), "#123456")
        self.hover(btn, False)
        self.assertEqual(btn.cget("bg"), "#123456")

    def test_button_created_disabled_gets_hover_once_enabled(self):
        btn = make_btn(self.root, "x", variant="primary", state=tk.DISABLED)
        rest = btn.cget("bg")
        self.hover(btn, True)
        self.assertEqual(btn.cget("bg"), rest)  # desabilitado nao reage
        self.hover(btn, False)
        btn.config(state=tk.NORMAL)
        self.hover(btn, True)
        self.assertEqual(btn.cget("bg"), COLORS["primary_active"])

    def test_danger_outline_has_red_border_and_text(self):
        btn = make_btn(self.root, "Deletar", variant="danger_outline")
        self.assertEqual(int(btn.cget("highlightthickness")), 1)
        self.assertEqual(btn.cget("highlightbackground"), COLORS["danger"])
        self.assertEqual(btn.cget("fg"), COLORS["danger"])

    def test_accent_uses_dark_text(self):
        self.assertEqual(make_btn(self.root, "x", variant="accent").cget("fg"), COLORS["accent_fg"])


class ToggleButtonTest(TkTestCase):
    def test_active_state_is_visual(self):
        toggle = make_toggle(self.root, "Anotar")
        off_bg = toggle.cget("bg")
        toggle.set_active(True)
        self.assertTrue(toggle.active)
        self.assertEqual(toggle.cget("bg"), COLORS["primary_soft"])
        self.assertEqual(toggle.cget("fg"), COLORS["primary"])
        toggle.set_active(False)
        self.assertEqual(toggle.cget("bg"), off_bg)

    def test_leave_keeps_state_changed_during_hover(self):
        toggle = make_toggle(self.root, "Anotar")
        self.hover(toggle, True)
        toggle.set_active(True)  # atalho de teclado com o mouse em cima
        self.hover(toggle, False)
        self.assertEqual(toggle.cget("bg"), COLORS["primary_soft"])

    def test_is_still_a_tk_button(self):
        toggle = make_toggle(self.root, "Anotar", state=tk.DISABLED)
        self.assertIsInstance(toggle, tk.Button)
        toggle.config(state=tk.NORMAL, text="Outro")
        self.assertEqual(toggle.cget("text"), "Outro")


# ── Sidebar ──────────────────────────────────────────────────────────────────

_NOOP_PREFIXES = ("on_", "toggle_", "reset_", "undo_", "rotate_", "apply_")


class _Profile:
    def __init__(self, keys):
        self._keys = keys

    def get_key(self, action_id):
        return self._keys.get(action_id)


class _SidebarTool(SidebarPanelMixin, UIControlsMixin):
    def __init__(self, root, *, tracking=True):
        self.window = root
        self.tracking_enabled = tracking
        self.manual_id_var = tk.StringVar(master=root)
        self.annotation_mode = self.selection_mode = self.remove_mode = False
        self.pan_mode = self.edit_id_mode = False
        self.info_var = tk.StringVar(master=root)

    def __getattr__(self, name):
        if name.startswith(_NOOP_PREFIXES):
            return lambda *a, **k: None
        raise AttributeError(name)

    def update_class_panel(self, *a, **k):
        pass

    def build_status_message(self):
        return ""


class SidebarTest(TkTestCase):
    def build(self, **kw):
        tool = _SidebarTool(self.root, **kw)
        tool._build_sidebar(tk.Frame(self.root))
        return tool

    def test_all_labeled_buttons_exist_without_on_off_text(self):
        tool = self.build()
        for name in SIDEBAR_LABELS:
            text = getattr(tool, name).cget("text")
            self.assertNotIn("ON", text.split())
            self.assertNotIn("OFF", text.split())

    def test_tool_buttons_are_toggles(self):
        tool = self.build()
        for name in ("annotation_button", "selection_button", "remove_button", "pan_button", "edit_id_button"):
            self.assertIsInstance(getattr(tool, name), ToggleButton)

    def test_default_keys_without_keybind_service(self):
        tool = self.build()
        self.assertEqual(tool.annotation_button.cget("text"), f"Anotar{KEY_SEPARATOR}K")
        self.assertEqual(tool.quit_button.cget("text"), f"Sair{KEY_SEPARATOR}Esc")
        self.assertEqual(tool.remove_button.cget("text"), "Remover")

    def test_labels_follow_remapped_keys(self):
        tool = self.build()
        tool._keybind_service = SimpleNamespace(
            get_active_profile=lambda: _Profile({"toggle_draw": "q", "accept": "Return"})
        )
        tool.refresh_sidebar_labels()
        self.assertEqual(tool.annotation_button.cget("text"), f"Anotar{KEY_SEPARATOR}Q")

    def test_update_functions_drive_toggle_state(self):
        tool = self.build()
        tool.annotation_mode = True
        tool.update_annotation_button()
        tool.pan_mode = True
        tool.update_pan_button()
        self.assertTrue(tool.annotation_button.active)
        self.assertTrue(tool.pan_button.active)
        self.assertFalse(tool.selection_button.active)

    def test_edit_id_toggle_stays_off_without_tracking(self):
        tool = self.build(tracking=False)
        tool.edit_id_mode = True
        tool.update_edit_id_button()
        self.assertFalse(tool.edit_id_button.active)
        self.assertEqual(str(tool.edit_id_button.cget("state")), tk.DISABLED)

    def test_subclass_override_relabels_shared_button(self):
        class _KeypointLike(_SidebarTool):
            sidebar_label_overrides = {"edit_id_button": ButtonLabel("Visível/oculto", fixed_key="C")}

        tool = _KeypointLike(self.root)
        tool._build_sidebar(tk.Frame(self.root))
        self.assertEqual(tool.edit_id_button.cget("text"), f"Visível/oculto{KEY_SEPARATOR}C")


class _TopbarTool(TopbarPanelMixin):
    def __init__(self, root):
        self.window = root
        self.task_mode = SimpleNamespace(label="Detecção", value="detection")
        self.info_var = tk.StringVar(master=root)
        self.image_name_var = tk.StringVar(master=root)

    def __getattr__(self, name):
        if name.startswith(_NOOP_PREFIXES + ("open_",)):
            return lambda *a, **k: None
        raise AttributeError(name)


class TopbarTest(TkTestCase):
    def test_brand_mark_is_in_the_left_corner(self):
        tool = _TopbarTool(self.root)
        tool._build_topbar()
        inner = tool.brand_mark.master
        packed = inner.pack_slaves()
        self.assertIs(packed[0], tool.brand_mark)
        self.assertEqual(tool.brand_mark.pack_info()["side"], "left")

    def test_topbar_texts_are_in_portuguese(self):
        tool = _TopbarTool(self.root)
        tool._build_topbar()
        self.assertEqual(tool.open_folder_button.cget("text"), "Abrir pasta")
        self.assertEqual(tool.delete_image_button.cget("fg"), COLORS["danger"])


if __name__ == "__main__":
    unittest.main()
