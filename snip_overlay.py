"""Snipping Tool tarzı alan seçimi. Ekranın dondurulmuş görüntüsü üzerinde
karartma + seçim kutusu gösterir; seçilen bölgeyi kırpıp sinyalle yollar.

Oyun uyumluluğu notu: burada activateWindow()/setFocus() ÇAĞIRMIYORUZ. Bu
çağrılar aktif pencereyi değiştirir ve tam ekran oyunun odağı kaybedip
masaüstüne düşmesine sebep olur. Odak almadığımız için Qt'nin keyPressEvent'i
de çalışmaz — Esc'yi zaten kısayollar için kullandığımız 'keyboard' kütüphanesi
ile düşük seviyeden dinliyoruz.
"""
import keyboard
from PySide6.QtCore import Qt, QRect, QRectF, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

ACCENT = QColor("#c0fa45")
MIN_SELECTION = 8  # px — bundan küçük seçimler kazara tıklama sayılır


class SnipOverlay(QWidget):
    region_selected = Signal(QPixmap, QRect)  # kırpılmış görüntü + global konum
    cancelled = Signal()
    failed = Signal(str)
    _esc_pressed = Signal()                   # keyboard thread'inden ana thread'e

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._shot = None
        self._geo = None
        self._origin = None
        self._cur = None
        self._esc_hook = None
        self._esc_pressed.connect(self._cancel)

    def start(self):
        # Fare hangi ekrandaysa o ekranı yakala (çoklu monitör desteği)
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            self.failed.emit("Ekran bulunamadı. Uygulamayı yeniden başlatmayı deneyin.")
            return
        self._geo = screen.geometry()
        self._shot = screen.grabWindow(0)  # overlay açılmadan ÖNCE tek kare al
        if self._shot.isNull():
            self._shot = None
            self.failed.emit("Ekran görüntüsü alınamadı. Biraz sonra yeniden deneyin.")
            return
        self._origin = self._cur = None
        self.setGeometry(self._geo)
        self.show()
        self.raise_()          # üste al, ama aktif pencereyi değiştirme
        self._hook_escape()

    # --- Esc dinleme (odak gerektirmeyen düşük seviye hook) ------------------

    def _hook_escape(self):
        self._unhook_escape()
        try:
            self._esc_hook = keyboard.on_press_key(
                "esc", lambda _: self._esc_pressed.emit(), suppress=False
            )
        except Exception:
            self._esc_hook = None

    def _unhook_escape(self):
        if self._esc_hook is not None:
            try:
                keyboard.unhook(self._esc_hook)
            except Exception:
                pass
            self._esc_hook = None

    def _finish(self):
        """Overlay'i kapatırken hook'u da bırak — arka planda Esc dinlemeye devam etmesin."""
        self._unhook_escape()
        self.hide()

    def _cancel(self):
        if not self.isVisible():
            return
        self._finish()
        self.cancelled.emit()

    # --- fare ---------------------------------------------------------------

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self._cancel()
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self._origin = self._cur = e.position().toPoint()
            self.update()

    def mouseMoveEvent(self, e):
        if self._origin is not None:
            self._cur = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        # Son mouseMove olayı henüz işlenmemiş olsa da bırakılan nokta doğrudur.
        rect = QRect(self._origin, e.position().toPoint()).normalized()
        rect = rect.intersected(self.rect())
        self._origin = self._cur = None
        self._finish()

        if rect.width() < MIN_SELECTION or rect.height() < MIN_SELECTION:
            self.cancelled.emit()
            return

        # Yüksek DPI ekranlarda mantıksal -> fiziksel piksel dönüşümü
        crop = crop_selection(self._shot, rect)
        if crop.isNull():
            self.failed.emit("Seçilen alanın ekran görüntüsü alınamadı.")
            return
        self.region_selected.emit(crop, rect.translated(self._geo.topLeft()))

    # --- çizim --------------------------------------------------------------

    def paintEvent(self, e):
        if self._shot is None:
            return
        p = QPainter(self)
        p.drawPixmap(self.rect(), self._shot)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))  # karartma

        if self._origin is not None and self._cur is not None:
            r = QRect(self._origin, self._cur).normalized()
            dpr = self._shot.devicePixelRatio()
            src = QRectF(r.x() * dpr, r.y() * dpr, r.width() * dpr, r.height() * dpr)
            p.drawPixmap(QRectF(r), self._shot, src)  # seçim içi parlak
            p.setPen(QPen(ACCENT, 2))
            p.drawRect(r)
        else:
            p.setPen(QColor(255, 255, 255, 200))
            p.drawText(
                self.rect().adjusted(0, 24, 0, 0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                "Çevrilecek alanı sürükleyerek seç  •  İptal: Esc / Sağ tık",
            )


def crop_selection(shot: QPixmap, rect: QRect) -> QPixmap:
    """Mantıksal seçim koordinatlarını fiziksel ekran piksellerine çevir."""
    dpr = shot.devicePixelRatio()
    x1, y1 = round(rect.x() * dpr), round(rect.y() * dpr)
    x2, y2 = round((rect.x() + rect.width()) * dpr), round((rect.y() + rect.height()) * dpr)
    physical = QRect(x1, y1, x2 - x1, y2 - y1).intersected(shot.rect())
    return shot.copy(physical) if not physical.isEmpty() else QPixmap()
