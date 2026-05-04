import unittest


class OBBToolContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from app.annotation_obb.tool import OBBAnnotationTool
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(f"Dependencia opcional ausente para contrato OBB: {exc}") from exc
        cls.Tool = OBBAnnotationTool

    def test_tool_provides_methods_required_by_reused_ui(self):
        required = [
            "update_display",
            "_draw_roi_overlay_on_canvas",
            "_draw_active_manual_rectangle",
            "toggle_pan_mode",
            "on_zoom",
            "reset_zoom",
            "update_canvas_cursor",
            "current_open_target_path",
            "current_deletable_image_path",
            "on_accept",
            "on_reject",
            "on_quit",
            "on_export_dataset",
            "update_annotation_button",
            "update_remove_button",
            "update_selection_button",
            "update_edit_id_button",
        ]

        missing = [name for name in required if not hasattr(self.Tool, name)]

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
