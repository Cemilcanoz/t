"""Real Qt worker signals keep OCR text available after a failed translation."""
import io
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from unittest.mock import patch
from PIL import Image
from PySide6.QtCore import QEventLoop, QRect, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication
from main import OcrTranslateWorker, TApp
import config


class WorkerFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait_for(self, predicate):
        loop = QEventLoop()
        poll = QTimer()
        poll.timeout.connect(lambda: loop.quit() if predicate() else None)
        poll.start(10)
        QTimer.singleShot(3000, loop.quit)
        loop.exec()
        poll.stop()
        self.assertTrue(predicate(), "Qt worker result was not delivered")

    @patch("main.config.load", return_value={**config.DEFAULTS, "show_floating_logo": False})
    @patch("main.HotkeyManager.register", return_value=True)
    @patch("main.crash_reporter.log_exception")
    @patch("main.ocr_engine.recognize", return_value="Please open the window.")
    @patch("main.translator.translate", side_effect=[RuntimeError("Service busy"), "Lütfen pencereyi açın."])
    def test_error_then_retry_reuses_ocr(self, translate, recognize, log, register, load):
        t = TApp(self.app)
        image = QPixmap(300, 60)
        image.fill()
        try:
            t.on_region(image, QRect(20, 20, 300, 60))
            self.wait_for(lambda: t.card._error == "Service busy")
            self.assertEqual(t.card._original, "Please open the window.")
            t.card.btn_retry.click()
            self.wait_for(lambda: t.card._translated == "Lütfen pencereyi açın.")
            self.assertEqual(recognize.call_count, 1)
            self.assertEqual(translate.call_count, 2)
            self.assertFalse(t.card.btn_retry.isVisible())
        finally:
            t.hotkeys.unregister()
            t.tray.hide()
            t.logo.close()
            if t.card is not None:
                t.card.close()

    @patch("main.translator.translate")
    @patch("main.ocr_engine.recognize")
    def test_cancelled_job_makes_no_service_request(self, recognize, translate):
        worker = OcrTranslateWorker(b"not-used", "en", "tr")
        worker.cancelled.set()
        worker.run()
        recognize.assert_not_called()
        translate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
