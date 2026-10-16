"""Eski ayarlardan gelen Çince dil kodunun OCR motoruyla uyumlu olması."""
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from PIL import Image

import ocr_engine


class OcrLanguageTests(unittest.TestCase):
    def setUp(self):
        ocr_engine._cache.clear()

    @patch("ocr_engine._is_supported", side_effect=lambda tag: tag == "zh-Hans")
    def test_legacy_simplified_chinese_code(self, supported):
        ocr_engine._cache.clear()
        self.assertEqual(ocr_engine.resolve_language("zh-CN"), "zh-Hans")
        supported.assert_called_once_with("zh-Hans")

    @patch("ocr_engine.available_languages", return_value=["tr"])
    @patch("ocr_engine._is_supported", side_effect=lambda tag: tag == "tr")
    def test_english_uses_installed_turkish_without_install(self, supported, available):
        self.assertEqual(ocr_engine.resolve_language("en"), "tr")

    @patch("ocr_engine.available_languages", return_value=["tr"])
    @patch("ocr_engine._is_supported", side_effect=lambda tag: tag == "tr")
    def test_never_falls_back_to_different_script(self, supported, available):
        self.assertIsNone(ocr_engine.resolve_language("ja"))

    @patch("ocr_engine.available_languages", return_value=[])
    @patch("ocr_engine._is_supported")
    def test_installing_language_after_failure_is_detected(self, supported, available):
        supported.return_value = False
        self.assertIsNone(ocr_engine.resolve_language("ja"))
        self.assertNotIn("ja", ocr_engine._cache)
        supported.side_effect = lambda tag: tag == "ja"
        self.assertEqual(ocr_engine.resolve_language("ja"), "ja")

    @patch("ocr_engine.available_languages", return_value=["tr"])
    @patch("ocr_engine._is_supported")
    def test_new_requested_language_replaces_cached_fallback(self, supported, available):
        supported.side_effect = lambda tag: tag == "tr"
        self.assertEqual(ocr_engine.resolve_language("en"), "tr")
        supported.side_effect = lambda tag: tag in ("en", "tr")
        self.assertEqual(ocr_engine.resolve_language("en"), "en")

    @patch("ocr_engine.available_languages", return_value=["pt-BR"])
    @patch("ocr_engine._is_supported", side_effect=lambda tag: tag == "pt-BR")
    def test_regional_installed_language_is_usable(self, supported, available):
        self.assertEqual(ocr_engine.resolve_language("en-US"), "pt-BR")


class OcrImageTests(unittest.TestCase):
    @patch("ocr_engine.OcrEngine", max_image_dimension=1000)
    def test_large_image_is_fitted_to_windows_limit(self, engine):
        prepared = ocr_engine._prepare_image(Image.new("RGBA", (2000, 500)))
        self.assertEqual(prepared.size, (1000, 250))
        self.assertEqual(prepared.mode, "RGB")

    @patch("ocr_engine.OcrEngine", max_image_dimension=1000)
    @patch("ocr_engine.resolve_language", return_value="tr")
    @patch("ocr_engine.winocr.recognize_pil_sync")
    def test_empty_ocr_gets_one_contrast_and_scale_retry(self, recognize, language, engine):
        recognize.side_effect = [{"lines": []}, {"lines": [{"text": "Hello world."}]}]
        self.assertEqual(ocr_engine.recognize(Image.new("RGB", (100, 40))), "Hello world.")
        self.assertEqual(recognize.call_count, 2)
        retry = recognize.call_args.args[0]
        self.assertEqual(retry.size, (200, 80))

    @patch("ocr_engine.resolve_language", return_value="tr")
    @patch("ocr_engine.winocr.recognize_pil_sync", return_value={"text": "Hello world.", "lines": []})
    def test_text_only_result_is_preserved(self, recognize, language):
        self.assertEqual(ocr_engine.recognize(Image.new("RGB", (100, 40))), "Hello world.")
        self.assertEqual(recognize.call_count, 1)

    @patch("ocr_engine.resolve_language", return_value="tr")
    @patch("ocr_engine.winocr.recognize_pil_sync", side_effect=OSError("native failure"))
    def test_native_failure_has_actionable_error(self, recognize, language):
        with self.assertRaisesRegex(RuntimeError, "Windows metin tanıma"):
            ocr_engine.recognize(Image.new("RGB", (100, 40)))

    @patch("ocr_engine.resolve_language", return_value="tr")
    @patch("ocr_engine.winocr.recognize_pil_sync", return_value={"lines": []})
    def test_blank_selection_remains_empty_after_bounded_retry(self, recognize, language):
        self.assertEqual(ocr_engine.recognize(Image.new("RGB", (100, 40))), "")
        self.assertEqual(recognize.call_count, 2)


if __name__ == "__main__":
    unittest.main()
