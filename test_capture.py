"""Selection cropping at Windows scaling factors and release coordinates."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from unittest.mock import patch
from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication
from snip_overlay import SnipOverlay, crop_selection


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_crop_uses_physical_pixels_at_fractional_dpi(self):
        shot = QPixmap(1250, 750)
        shot.fill(QColor("white"))
        shot.setDevicePixelRatio(1.25)
        crop = crop_selection(shot, QRect(100, 80, 200, 100))
        self.assertEqual((crop.width(), crop.height()), (250, 125))

    def test_outside_selection_does_not_return_entire_screenshot(self):
        shot = QPixmap(400, 200)
        self.assertTrue(crop_selection(shot, QRect(500, 500, 20, 20)).isNull())

    def test_release_uses_release_position_and_global_monitor_origin(self):
        overlay = SnipOverlay()
        overlay.resize(400, 200)
        overlay._geo = QRect(-400, 0, 400, 200)
        overlay._shot = QPixmap(400, 200)
        overlay._shot.fill(QColor("white"))
        overlay._origin = QPointF(10, 10).toPoint()
        overlay._cur = QPointF(10, 10).toPoint()  # no mouseMove received
        regions = []
        overlay.region_selected.connect(lambda image, rect: regions.append(rect))
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease, QPointF(110, 60), QPointF(110, 60),
            Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        )
        overlay.mouseReleaseEvent(event)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].topLeft().x(), -390)
        self.assertGreaterEqual(regions[0].width(), 100)
        overlay.close()


if __name__ == "__main__":
    unittest.main()
