"""A compact, movable translation card that never steals application focus."""
from PySide6.QtCore import Qt, QRect, QSize, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextBrowser,
    QToolButton, QVBoxLayout, QWidget,
)

import icons
import theme

MARGIN = 7
MIN_W, MIN_H = 330, 210
NONE, LEFT, RIGHT, TOP, BOTTOM = 0, 1, 2, 4, 8
_CURSORS = {
    LEFT: Qt.CursorShape.SizeHorCursor, RIGHT: Qt.CursorShape.SizeHorCursor,
    TOP: Qt.CursorShape.SizeVerCursor, BOTTOM: Qt.CursorShape.SizeVerCursor,
    LEFT | TOP: Qt.CursorShape.SizeFDiagCursor,
    RIGHT | BOTTOM: Qt.CursorShape.SizeFDiagCursor,
    RIGHT | TOP: Qt.CursorShape.SizeBDiagCursor,
    LEFT | BOTTOM: Qt.CursorShape.SizeBDiagCursor,
}
_LANG_NAMES = {
    "tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "fr": "Fransızca",
    "es": "İspanyolca", "it": "İtalyanca", "ru": "Rusça", "ja": "Japonca",
    "ko": "Korece", "zh-CN": "Çince", "ar": "Arapça", "pt": "Portekizce",
}


class ResultCard(QWidget):
    retry_requested = Signal()
    new_selection_requested = Signal()
    settings_requested = Signal()

    def __init__(self, cfg: dict):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setMinimumSize(MIN_W, MIN_H)
        self.setAccessibleName("T çeviri sonucu")
        self._original = self._translated = self._error = ""
        self._showing_original = False
        self._edge = NONE
        self._press_global = self._press_geo = None
        self._icon_color = theme.MUTED
        self._provider_name = "MyMemory" if cfg.get("provider", "mymemory") == "mymemory" else "Google"
        self._target = _LANG_NAMES.get(cfg.get("target_lang", "tr"), cfg.get("target_lang", "tr"))
        alpha = int(max(0.2, min(float(cfg["bg_opacity"]), 1.0)) * 255)
        self.setStyleSheet(theme.CONTROLS + f"""
            QFrame#card {{ background: rgba(16, 37, 29, {alpha});
                           border: 1px solid #56705b; border-radius: 4px; }}
            QLabel#title {{ color: #f5f1df; font-family: 'Georgia'; font-weight: 400; font-size: 22px; }}
            QLabel#language {{ color: #c0fa45; background: #29452c;
                               border-radius: 2px; padding: 4px 8px; font-size: 11px; }}
            QToolButton {{ background: transparent; border: none; padding: 6px; }}
            QToolButton:hover {{ background: #33573c; }}
            QToolButton#close:hover {{ background: #63483a; }}
            QPushButton#swap {{ background: #29452c; border: none;
                                padding: 5px 9px; font-size: 11px; }}
            QPushButton#retry {{ background: #c0fa45; color: #10251d;
                                 border: none; padding: 5px 10px; font-size: 11px; }}
            QTextBrowser {{ background: transparent; border: none; color: {cfg["text_color"]}; font-size: {int(cfg["font_size"])}pt; }}
            QProgressBar {{ background: #46634b; border: none; border-radius: 2px; }}
            QProgressBar::chunk {{ background: #c0fa45; border-radius: 2px; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        card = QFrame()
        card.setObjectName("card")
        root.addWidget(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 15, 18, 14)
        lay.setSpacing(12)
        lay.addWidget(theme.Masthead(compact=True))
        header = QHBoxLayout()
        header.setSpacing(10)
        self.title = QLabel("Çeviri")
        self.title.setObjectName("title")
        self.title.setWordWrap(True)
        header.addWidget(self.title)
        header.addStretch()
        self.btn_copy = self._tool_btn(icons.COPY, "Metni kopyala", self.copy_text)
        self.btn_close = self._tool_btn(icons.CLOSE, "Kapat", self.close)
        self.btn_close.setObjectName("close")
        header.addWidget(self.btn_copy)
        header.addWidget(self.btn_close)
        lay.addLayout(header)
        meta = QHBoxLayout()
        self.language = QLabel(self._target)
        self.language.setObjectName("language")
        meta.addWidget(self.language)
        meta.addStretch()
        self.btn_swap = QPushButton("Orijinal metin")
        self.btn_swap.setObjectName("swap")
        self.btn_swap.setIcon(icons.icon(icons.EYE, theme.MUTED))
        self.btn_swap.setIconSize(QSize(13, 13))
        self.btn_swap.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_swap.clicked.connect(self.toggle_original)
        meta.addWidget(self.btn_swap)
        lay.addLayout(meta)
        self.text = QTextBrowser()
        self.text.setMouseTracking(True)
        self.text.setOpenExternalLinks(False)
        self.text.setAccessibleName("Çeviri metni")
        self.text.document().setDocumentMargin(0)
        f = self.text.font()
        f.setPointSize(int(cfg["font_size"]))
        self.text.setFont(f)
        lay.addWidget(self.text, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.hide()
        lay.addWidget(self.progress)
        footer = QHBoxLayout()
        self.status = QLabel("Ekrandan çeviri")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.btn_settings = QPushButton("Ayarlar")
        self.btn_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_settings.clicked.connect(self.settings_requested.emit)
        footer.addWidget(self.btn_settings)
        self.btn_new = QPushButton("Yeni alan")
        self.btn_new.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_new.clicked.connect(self.new_selection_requested.emit)
        footer.addWidget(self.btn_new)
        self.btn_retry = QPushButton("Tekrar dene")
        self.btn_retry.setObjectName("retry")
        self.btn_retry.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_retry.clicked.connect(self.retry_requested.emit)
        self.btn_retry.hide()
        footer.addWidget(self.btn_retry)
        lay.addLayout(footer)
        self.btn_copy.setEnabled(False)
        self.btn_swap.setEnabled(False)

    def _tool_btn(self, svg: str, tip: str, slot) -> QToolButton:
        b = QToolButton()
        b.setIcon(icons.icon(svg, self._icon_color))
        b.setIconSize(QSize(17, 17))
        b.setFixedSize(30, 30)
        b.setToolTip(tip)
        b.setAccessibleName(tip)
        b.setCursor(Qt.CursorShape.ArrowCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.clicked.connect(slot)
        return b

    def set_loading(self):
        self._original = self._translated = self._error = ""
        self._showing_original = False
        self.title.setText("Çevriliyor")
        self.language.setText(self._target)
        self.text.setPlainText("Seçtiğin metin hazırlanıyor…")
        self.btn_swap.setText("Orijinal metin")
        self.btn_swap.setIcon(icons.icon(icons.EYE, theme.MUTED))
        self.btn_copy.setEnabled(False)
        self.btn_copy.setIcon(icons.icon(icons.COPY, self._icon_color))
        self.btn_swap.setEnabled(False)
        self.btn_retry.hide()
        self.progress.show()
        self.set_status("Metin okunuyor…")

    def set_status(self, message: str):
        self.status.setText(message)
        self.status.setStyleSheet("color: #c0fa45;")

    def set_result(self, original: str, translated: str):
        self._original, self._translated, self._error = original, translated, ""
        self._showing_original = False
        self.progress.hide()
        self.btn_retry.hide()
        if not original:
            self.title.setText("Metin bulunamadı")
            self.text.setPlainText("Yazının tamamını içine alan bir bölge seç. Küçük yazılarda sayfayı yakınlaştırmak yardımcı olabilir.")
            self.status.setText("Başka bir alan seçerek yeniden deneyebilirsin.")
            self.status.setStyleSheet("color: #b4c2ac;")
            self.btn_copy.setEnabled(False)
            self.btn_swap.setEnabled(False)
            self.btn_retry.show()
            return
        if not translated:
            self.set_error("Çeviri boş döndü. Bir kez daha deneyebilirsin.", original)
            return
        self._refresh()
        self.status.setText("Çeviri hazır · " + self._provider_name)
        self.status.setStyleSheet("color: #c0fa45;")

    def set_error(self, msg: str, original: str = ""):
        self._original, self._translated, self._error = original, "", msg
        self._showing_original = False
        self.progress.hide()
        self.title.setText("Çeviri tamamlanamadı")
        self.language.setText(self._target)
        self.btn_copy.setIcon(icons.icon(icons.COPY, self._icon_color))
        self.text.setPlainText(msg)
        self.status.setText("Tekrar deneyebilir veya metni görüntüleyebilirsin." if original else "Bir kez daha deneyebilirsin.")
        self.status.setStyleSheet("color: #efb98d;")
        self.btn_copy.setEnabled(False)
        self.btn_swap.setEnabled(bool(original))
        self.btn_swap.setText("Orijinal metin")
        self.btn_swap.setIcon(icons.icon(icons.EYE, theme.MUTED))
        self.btn_retry.show()

    def _refresh(self):
        self.btn_copy.setIcon(icons.icon(icons.COPY, self._icon_color))
        if self._showing_original:
            self.title.setText("Orijinal metin")
            self.language.setText("Ekrandan okunan")
            self.text.setPlainText(self._original)
            self.btn_swap.setText("Hataya dön" if self._error else "Çeviriye dön")
            self.btn_swap.setIcon(icons.icon(icons.EYE_OFF, theme.MUTED))
        else:
            self.title.setText("Çeviri tamamlanamadı" if self._error else "Çeviri")
            self.language.setText(self._target)
            self.text.setPlainText(self._error or self._translated)
            self.btn_swap.setText("Orijinal metin")
            self.btn_swap.setIcon(icons.icon(icons.EYE, theme.MUTED))
        self.btn_swap.setEnabled(bool(self._original))
        self.btn_copy.setEnabled(bool(self._original if self._showing_original else self._translated))
        self.btn_copy.setToolTip("Orijinal metni kopyala" if self._showing_original else "Çeviriyi kopyala")

    def toggle_original(self):
        if self._original:
            self._showing_original = not self._showing_original
            self._refresh()

    def copy_text(self):
        txt = self._original if self._showing_original else self._translated
        if not txt:
            return
        QGuiApplication.clipboard().setText(txt)
        self.btn_copy.setIcon(icons.icon(icons.CHECK, theme.TEAL))
        QTimer.singleShot(1000, lambda: self.btn_copy.setIcon(icons.icon(icons.COPY, self._icon_color)))

    # ----------------------------------------------------------- konumlandırma

    def show_for_rect(self, rect: QRect):
        """Kartı seçilen alanın üstüne koyar; yukarıda yer yoksa altına alır."""
        screen = (
            QGuiApplication.screenAt(rect.center())
            or QGuiApplication.primaryScreen()
        )
        area = screen.availableGeometry()
        w = max(390, min(rect.width() + 2 * MARGIN + 40, 620))
        h = 310
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
