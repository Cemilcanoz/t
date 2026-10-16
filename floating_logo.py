"""Ekranda yüzen, sürüklenebilir, yarı saydam 'T' logosu.
Tıklayınca ekran seçimi başlatır."""
from PySide6.QtCore import Qt, QPoint, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

SIZE = 56
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
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("T ekran çevirisi başlat")
        self.setWindowOpacity(0.88)

    def enterEvent(self, e):
        self._hovered = True
        self.setWindowOpacity(1.0)
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.setWindowOpacity(0.88)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 45))
        p.drawRoundedRect(QRectF(4, 6, 48, 48), 5, 5)
        gradient = QLinearGradient(5, 4, 49, 51)
        gradient.setColorAt(0, QColor("#c0fa45"))
        gradient.setColorAt(1, QColor("#c0fa45"))
        p.setBrush(gradient)
        p.setPen(QPen(QColor("#f5f1df" if self._hovered else "#10251d"), 1.2))
        p.drawRoundedRect(QRectF(4, 3, 48, 48), 4, 4)
        p.setPen(QColor("#10251d"))
        p.setFont(QFont("Georgia", 27))
        p.drawText(QRectF(4, 1, 48, 48), Qt.AlignmentFlag.AlignCenter, "T")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#f5f1df"))
        p.drawEllipse(QRectF(41, 41, 8, 8))

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
