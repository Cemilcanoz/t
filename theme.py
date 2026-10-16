"""Shared colors and controls for T's compact desktop interface."""

BACKGROUND = "#10251d"
SURFACE = "#193329"
TEXT = "#f5f1df"
MUTED = "#b4c2ac"
ACCENT = "#c0fa45"
TEAL = "#c0fa45"

CONTROLS = """
    QWidget { font-family: 'Segoe UI'; color: #f5f1df; font-size: 13px; }
    QLabel { background: transparent; border: none; }
    QLabel#brand { background: #c0fa45; color: #10251d; border-radius: 2px;
                   font-size: 21px; font-weight: 700; }
    QLabel#muted { color: #b4c2ac; font-size: 12px; }
    QToolTip { background: #254435; color: #f5f1df; border: 1px solid #56705b;
               padding: 6px; }
    QToolButton, QPushButton { background: #244333; border: 1px solid #46634b;
                              border-radius: 3px; padding: 7px 12px; }
    QToolButton:hover, QPushButton:hover { background: #33573c; border-color: #a5cc62; }
    QToolButton:pressed, QPushButton:pressed { background: #416646; }
    QToolButton:disabled, QPushButton:disabled { color: #8d9d85; border-color: #254435; }
    QPushButton#primary { background: #c0fa45; color: #10251d; border: none;
                         font-weight: 600; padding: 9px 22px; }
    QPushButton#primary:hover { background: #d3ff78; }
    QComboBox, QSpinBox, QKeySequenceEdit { background: #10251d; border: 1px solid #46634b;
                                          border-radius: 3px; padding: 7px 10px;
                                          min-height: 20px; }
    QComboBox:focus, QSpinBox:focus, QKeySequenceEdit:focus { border-color: #c0fa45; }
    QKeySequenceEdit QLineEdit { background: #10251d; color: #f5f1df; border: none;
                                 selection-background-color: #41623a; }
    QComboBox::drop-down { border: none; width: 24px; }
    QComboBox QAbstractItemView { background: #193329; color: #f5f1df;
        selection-background-color: #41623a; border: 1px solid #46634b; padding: 4px; }
    QSlider::groove:horizontal { background: #46634b; height: 4px; border-radius: 2px; }
    QSlider::sub-page:horizontal { background: #c0fa45; border-radius: 2px; }
    QSlider::handle:horizontal { background: #f5f1df; width: 15px; margin: -6px 0;
                                border: 2px solid #c0fa45; border-radius: 3px; }
    QScrollBar:vertical { background: transparent; width: 7px; margin: 2px; }
    QScrollBar::handle:vertical { background: #56705b; border-radius: 3px; min-height: 24px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


# A compact editorial masthead, shared by the preferences and result card.
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class Masthead(QWidget):
    def __init__(self, compact=False, parent=None):
        super().__init__(parent)
        self.compact = compact
        self.setFixedHeight(48 if compact else 116)
        self.setAccessibleName("T — Seç. Çevir. Anla.")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(ACCENT))
        p.setPen(QColor(BACKGROUND))
        if self.compact:
            p.setFont(QFont("Georgia", 24))
            p.drawText(QRectF(14, 0, 42, 48), Qt.AlignmentFlag.AlignVCenter, "T")
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            p.drawText(QRectF(56, 0, self.width()-68, 48), Qt.AlignmentFlag.AlignVCenter, "SEÇ. ÇEVİR. ANLA.")
        else:
            p.setFont(QFont("Georgia", 45))
            p.drawText(QRectF(20, 12, self.width()-110, 70), Qt.AlignmentFlag.AlignVCenter, "Bir başka dil.")
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(QRectF(23, 83, self.width()-46, 22), Qt.AlignmentFlag.AlignVCenter, "T  /  EKRAN ÇEVİRİSİ       SEÇ. ÇEVİR. ANLA.")
            # Two intersecting reading frames: the same text, two languages.
            x = self.width()-87
            p.setPen(QPen(QColor(BACKGROUND), 1))
            p.drawRect(QRectF(x, 22, 43, 46))
            p.drawRect(QRectF(x+18, 38, 43, 46))
            p.setFont(QFont("Georgia", 23))
            p.drawText(QRectF(x, 20, 43, 46), Qt.AlignmentFlag.AlignCenter, "a")
            p.drawText(QRectF(x+18, 37, 43, 46), Qt.AlignmentFlag.AlignCenter, "â")
