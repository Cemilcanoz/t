"""Çeviri sonucu kartı.

Üç önemli davranış:

1) Kenarlardan boyutlandırma — pencere çerçevesiz olduğu için Windows'un kendi
   boyutlandırma tutamakları yok. Kartın etrafında MARGIN kadar şeffaf bir bant
   bırakıyoruz; fare bu banda girdiğinde hangi kenarda olduğunu hesaplayıp
   imleci değiştiriyor ve sürüklemeyi boyutlandırmaya çeviriyoruz.

2) Odak çalmama — WA_ShowWithoutActivating + WindowDoesNotAcceptFocus sayesinde
   kart göründüğünde aktif pencere değişmez. Bu olmadan tam ekran oyunlar
   odağı kaybedip masaüstüne düşer.

3) İkonlar SVG (bkz. icons.py), emoji değil.
"""
from PySide6.QtCore import Qt, QRect, QSize, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QTextBrowser, QToolButton, QVBoxLayout, QWidget,
)

import icons

MARGIN = 7        # kenar yakalama bandı genişliği (px)
MIN_W, MIN_H = 240, 110

# Kenar bit bayrakları — köşeler ikisinin birleşimi (ör. SOL|UST)
NONE, LEFT, RIGHT, TOP, BOTTOM = 0, 1, 2, 4, 8

_CURSORS = {
    LEFT: Qt.CursorShape.SizeHorCursor,
    RIGHT: Qt.CursorShape.SizeHorCursor,
    TOP: Qt.CursorShape.SizeVerCursor,
    BOTTOM: Qt.CursorShape.SizeVerCursor,
    LEFT | TOP: Qt.CursorShape.SizeFDiagCursor,
    RIGHT | BOTTOM: Qt.CursorShape.SizeFDiagCursor,
    RIGHT | TOP: Qt.CursorShape.SizeBDiagCursor,
    LEFT | BOTTOM: Qt.CursorShape.SizeBDiagCursor,
}


class ResultCard(QWidget):
    def __init__(self, cfg: dict):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)          # butona basılmadan da imleç değişsin
        self.setMinimumSize(MIN_W, MIN_H)

        self._original = ""
        self._translated = ""
        self._showing_original = False
        self._edge = NONE                    # sürükleme başlarken yakalanan kenar
        self._press_global = None
        self._press_geo = None

        self._icon_color = "#d8d8e0"
        alpha = int(float(cfg["bg_opacity"]) * 255)

        root = QVBoxLayout(self)
        root.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)  # yakalama bandı

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"""
            #card {{
                background-color: rgba(24, 24, 30, {alpha});
                border: 1px solid rgba(255, 255, 255, 26);
                border-radius: 12px;
            }}
            QToolButton {{
                background: transparent; border: none;
                padding: 3px; border-radius: 6px;
            }}
            QToolButton:hover {{ background: rgba(255, 255, 255, 34); }}
            QLabel#title {{ color: #9a8cff; font-weight: 600; font-size: 12px; }}
            QTextBrowser {{
                background: transparent; border: none;
                color: {cfg["text_color"]};
            }}
            QScrollBar:vertical {{
                background: transparent; width: 8px; margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 45); border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(13, 9, 13, 11)
        lay.setSpacing(5)

        header = QHBoxLayout()
        header.setSpacing(2)
        self.title = QLabel("Çeviri")
        self.title.setObjectName("title")
        header.addWidget(self.title)
        header.addStretch()

        self.btn_copy = self._tool_btn(icons.COPY, "Çeviriyi kopyala", self.copy_text)
        self.btn_swap = self._tool_btn(
            icons.EYE, "Orijinal metni göster", self.toggle_original
        )
        self.btn_close = self._tool_btn(icons.CLOSE, "Kapat", self.close)
        for b in (self.btn_copy, self.btn_swap, self.btn_close):
            header.addWidget(b)
        lay.addLayout(header)

        self.text = QTextBrowser()
        self.text.setMouseTracking(True)
        f = self.text.font()
        f.setPointSize(int(cfg["font_size"]))
        self.text.setFont(f)
        lay.addWidget(self.text, 1)

    def _tool_btn(self, svg: str, tip: str, slot) -> QToolButton:
        b = QToolButton()
        b.setIcon(icons.icon(svg, self._icon_color))
        b.setIconSize(QSize(15, 15))
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.ArrowCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.clicked.connect(slot)
        return b

    # ------------------------------------------------------------------ içerik

    def set_loading(self):
        self.title.setText("Çeviri")
        self.text.setPlainText("Metin okunuyor ve çevriliyor…")

    def set_result(self, original: str, translated: str):
        self._original = original
        self._translated = translated
        self._showing_original = False
        if not original:
            self.title.setText("Sonuç yok")
            self.text.setPlainText("Seçilen alanda okunabilir metin bulunamadı.")
        else:
            self._refresh()

    def set_error(self, msg: str):
        self.title.setText("Hata")
        self.text.setPlainText(msg)

    def _refresh(self):
        if self._showing_original:
            self.title.setText("Orijinal (OCR)")
            self.text.setPlainText(self._original)
            self.btn_swap.setIcon(icons.icon(icons.EYE_OFF, self._icon_color))
            self.btn_swap.setToolTip("Çeviriye dön")
        else:
            self.title.setText("Çeviri")
            self.text.setPlainText(self._translated)
            self.btn_swap.setIcon(icons.icon(icons.EYE, self._icon_color))
            self.btn_swap.setToolTip("Orijinal metni göster")

    def toggle_original(self):
        if not self._original:
            return
        self._showing_original = not self._showing_original
        self._refresh()

    def copy_text(self):
        txt = self._original if self._showing_original else self._translated
        if not txt:
            return
        QGuiApplication.clipboard().setText(txt)
        # Kısa bir tik göster, sonra kopyala ikonuna dön
        self.btn_copy.setIcon(icons.icon(icons.CHECK, "#6ee7a8"))
        QTimer.singleShot(
            1000,
            lambda: self.btn_copy.setIcon(icons.icon(icons.COPY, self._icon_color)),
        )

    # ----------------------------------------------------------- konumlandırma

    def show_for_rect(self, rect: QRect):
        """Kartı seçilen alanın üstüne koyar; yukarıda yer yoksa altına alır."""
        screen = (
            QGuiApplication.screenAt(rect.center())
            or QGuiApplication.primaryScreen()
        )
        area = screen.availableGeometry()
        w = max(MIN_W + 80, min(rect.width() + 2 * MARGIN + 40, 580))
        h = 200
        self.resize(w, h)

        x = min(max(rect.x() - MARGIN, area.left() + 4), area.right() - w - 4)
        y = rect.y() - h - 6
        if y < area.top() + 4:
            y = min(rect.bottom() + 6, area.bottom() - h - 4)
        self.move(x, y)
        self.show()
        self.raise_()   # üstte olsun ama aktif pencere olmasın (odak çalma yok)

    # ------------------------------------------------- taşıma ve boyutlandırma

    def _hit_test(self, pos) -> int:
        """Fare konumunun hangi kenar bandında olduğunu bit bayrağı olarak döner."""
        edge = NONE
        if pos.x() <= MARGIN:
            edge |= LEFT
        elif pos.x() >= self.width() - MARGIN:
            edge |= RIGHT
        if pos.y() <= MARGIN:
            edge |= TOP
        elif pos.y() >= self.height() - MARGIN:
            edge |= BOTTOM
        return edge

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        self._edge = self._hit_test(e.position().toPoint())
        self._press_global = e.globalPosition().toPoint()
        self._press_geo = self.geometry()

    def mouseMoveEvent(self, e):
        # Basılı değilken: sadece imleci güncelle
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            edge = self._hit_test(e.position().toPoint())
            self.setCursor(_CURSORS.get(edge, Qt.CursorShape.ArrowCursor))
            return

        if self._press_global is None:
            return
        delta = e.globalPosition().toPoint() - self._press_global

        if self._edge == NONE:          # kenarda değil → pencereyi taşı
            self.move(self._press_geo.topLeft() + delta)
            return

        g = QRect(self._press_geo)      # kenarda → boyutlandır
        if self._edge & LEFT:
            g.setLeft(min(g.left() + delta.x(), g.right() - MIN_W))
        if self._edge & RIGHT:
            g.setRight(max(g.right() + delta.x(), g.left() + MIN_W))
        if self._edge & TOP:
            g.setTop(min(g.top() + delta.y(), g.bottom() - MIN_H))
        if self._edge & BOTTOM:
            g.setBottom(max(g.bottom() + delta.y(), g.top() + MIN_H))
        self.setGeometry(g)

    def mouseReleaseEvent(self, e):
        self._edge = NONE
        self._press_global = None
        self._press_geo = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, e):
        if self._press_global is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
