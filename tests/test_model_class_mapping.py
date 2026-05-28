import unittest


class ModelClassMappingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from backend.annotation.core.services.class_service import ClassServiceMixin
            from backend.annotation.detection.frame_model_helpers import FrameModelHelpersMixin
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(f"Dependencia opcional ausente para teste de modelo: {exc}") from exc

        class DummyModelClassMapper(FrameModelHelpersMixin, ClassServiceMixin):
            def __init__(self, target_classes):
                self.target_classes = list(target_classes)
                self.class_to_category_id = {}
                self.categories = []

        cls.Mapper = DummyModelClassMapper

    def test_resolves_model_label_to_matching_ui_class(self):
        mapper = self.Mapper(["face", "text_region", "doc_id"])

        category_id = mapper._resolve_category_id("text_region", 1)

        self.assertEqual(category_id, 2)
        self.assertEqual(mapper.class_to_category_id["text_region"], 2)

    def test_resolves_label_case_insensitively_to_ui_class(self):
        mapper = self.Mapper(["face", "text_region", "doc_id"])

        category_id = mapper._resolve_category_id("DOC_ID", 2)

        self.assertEqual(category_id, 3)
        self.assertEqual(mapper.categories[0]["name"], "doc_id")

    def test_falls_back_to_model_class_index_when_label_does_not_match(self):
        mapper = self.Mapper(["face", "text_region", "doc_id"])

        category_id = mapper._resolve_category_id("class_1", 1)

        self.assertEqual(category_id, 2)
        self.assertEqual(mapper.class_to_category_id["text_region"], 2)

    def test_ignores_unknown_model_class_without_index_match(self):
        mapper = self.Mapper(["face", "text_region"])

        category_id = mapper._resolve_category_id("signature", 5)

        self.assertIsNone(category_id)
        self.assertEqual(mapper.categories, [])

    def test_register_category_uses_ui_order_even_when_registered_late(self):
        mapper = self.Mapper(["face", "text_region", "doc_id"])

        category_id = mapper.register_category("doc_id")

        self.assertEqual(category_id, 3)


if __name__ == "__main__":
    unittest.main()
