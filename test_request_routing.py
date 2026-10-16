"""Arka plan işlerinin yalnızca ait oldukları sonuç kartını güncellediğini doğrular."""
import unittest
from unittest.mock import patch

from main import TApp


class _Card:
    def __init__(self):
        self.result = None
        self.error = None

    def set_result(self, original, translated):
        self.result = (original, translated)

    def set_error(self, message, original=""):
        self.error = message
        self.original = original

    def set_status(self, message):
        self.status = message

    def set_loading(self):
        self.loading = True


class _Overlay:
    def isVisible(self):
        return False

    def start(self):
        pass


class _Logo:
    def hide(self):
        pass


class RequestRoutingTests(unittest.TestCase):
    def setUp(self):
        # Bu metotları sınamak için QApplication veya gerçek pencere gerekmez.
        self.app = TApp.__new__(TApp)
        self.app._request_id = 2
        self.app.card = _Card()

    def test_stale_result_is_ignored(self):
        self.app.on_done(1, "eski", "old")
        self.assertIsNone(self.app.card.result)

    def test_current_result_is_applied(self):
        self.app.on_done(2, "yeni", "new")
        self.assertEqual(self.app.card.result, ("yeni", "new"))

    def test_stale_error_is_ignored(self):
        self.app.on_error(1, "eski hata")
        self.assertIsNone(self.app.card.error)

    def test_error_preserves_recognized_text(self):
        self.app.on_recognized(2, "Read text")
        self.app.on_error(2, "Service busy")
        self.assertEqual(self.app.card.original, "Read text")

    def test_stale_recognized_text_is_ignored(self):
        self.app._last_original = "new"
        self.app.on_recognized(1, "old")
        self.assertEqual(self.app._last_original, "new")

    def test_stale_progress_is_ignored(self):
        self.app.card.status = None
        self.app.on_status(1, "old")
        self.assertIsNone(self.app.card.status)

    @patch("main.TApp._submit_worker")
    def test_retry_uses_existing_capture_and_text(self, submit):
        self.app._last_capture = b"image"
        self.app._last_original = "read once"
        self.app._worker = None
        self.app.retry_translation()
        submit.assert_called_once_with(3)
        self.assertEqual(self.app._last_original, "read once")
        self.assertTrue(self.app.card.loading)

    @patch("main.QTimer.singleShot")
    def test_repeated_hotkey_schedules_only_one_capture(self, single_shot):
        self.app.overlay = _Overlay()
        self.app.logo = _Logo()
        self.app.card = None
        self.app._snip_pending = False

        self.app.trigger_snip()
        self.app.trigger_snip()

        single_shot.assert_called_once()


if __name__ == "__main__":
    unittest.main()
