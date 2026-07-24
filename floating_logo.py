"""Ekranda yüzen, sürüklenebilir, yarı saydam 'T' logosu.
Tıklayınca ekran seçimi başlatır."""
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

SIZE = 52
DRAG_THRESHOLD = 6  # px — bundan az hareket "tıklama" sayılır


class FloatingLogo(QWidget):
    clicked = Signal()
    moved = Signal(QPoint)

    def __init__(self, pixmap: QPixmap):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Göründüğünde aktif pencereyi değiştirmesin — yoksa tam ekran oyun
        # odağı kaybedip masaüstüne düşer.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(SIZE, SIZE)
        self.setToolTip("T — Çevirmek için tıkla, taşımak için sürükle")
        self._pix = pixmap
        self._press_global = None
        self._press_window = None
        self._dragging = False
        self.setWindowOpacity(0.65)

    def enterEvent(self, e):
        self.setWindowOpacity(1.0)

    def leaveEvent(self, e):
        self.setWindowOpacity(0.65)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self._pix)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_global = e.globalPosition().toPoint()
            self._press_window = self.pos()
            self._dragging = False

    def mouseMoveEvent(self, e):
        if self._press_global is None:
            return
        delta = e.globalPosition().toPoint() - self._press_global
        if delta.manhattanLength() > DRAG_THRESHOLD:
            self._dragging = True
        if self._dragging:
            self.move(self._press_window + delta)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._press_global is None:
            return
        was_drag = self._dragging
        self._press_global = None
        self._dragging = False
        if was_drag:
            self.moved.emit(self.pos())
        else:
            self.clicked.emit()