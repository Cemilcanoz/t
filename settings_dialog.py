"""Ayarlar penceresi."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QKeySequenceEdit, QLabel, QPushButton, QSlider, QSpinBox,
)

import ocr_engine

TARGET_LANGS = {
    "Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr",
    "İspanyolca": "es", "İtalyanca": "it", "Rusça": "ru", "Japonca": "ja",
    "Korece": "ko", "Çince (Basit)": "zh-CN", "Arapça": "ar", "Portekizce": "pt",
}
OCR_LANGS = {
    "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", "Fransızca": "fr",
    "İspanyolca": "es", "İtalyanca": "it", "Rusça": "ru", "Japonca": "ja",
    "Korece": "ko", "Çince (Basit)": "zh-CN",
}


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("T — Ayarlar")
        self.cfg = cfg
        self._color = cfg["text_color"]

        form = QFormLayout(self)

        self.cmb_target = QComboBox()
        self._fill(self.cmb_target, TARGET_LANGS, cfg["target_lang"])
        form.addRow("Hedef dil (çeviri):", self.cmb_target)

        self.cmb_ocr = QComboBox()
        self._fill_ocr(self.cmb_ocr, cfg["ocr_lang"])
        form.addRow("Okunacak metnin dili (OCR):", self.cmb_ocr)

        installed = ocr_engine.available_languages()
        note = QLabel(
            f"Kurulu OCR dilleri: {', '.join(installed) or 'yok'}\n"
            "Kurulu olmayan diller ⚠ ile işaretli — Latin alfabesindeyse yine de\n"
            "okunur. Yeni dil: Ayarlar > Zaman ve Dil > Dil ve bölge > Dil ekle."
        )
        note.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow(note)

        self.key_edit = QKeySequenceEdit(QKeySequence(cfg["hotkey"]))
        form.addRow("Kısayol tuşu:", self.key_edit)

        self.spin_font = QSpinBox()
        self.spin_font.setRange(8, 40)
        self.spin_font.setValue(int(cfg["font_size"]))
        form.addRow("Yazı boyutu:", self.spin_font)

        self.btn_color = QPushButton()
        self.btn_color.clicked.connect(self._pick_color)
        self._paint_color_btn()
        form.addRow("Yazı rengi:", self.btn_color)

        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(20, 100)
        self.sld_opacity.setValue(int(float(cfg["bg_opacity"]) * 100))
        form.addRow("Arka plan opaklığı:", self.sld_opacity)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def _fill(combo: QComboBox, langs: dict, current: str):
        for name, code in langs.items():
            combo.addItem(name, code)
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    @staticmethod
    def _fill_ocr(combo: QComboBox, current: str):
        """Kurulu olmayan OCR dillerini ⚠ ile işaretle."""
        installed = set(ocr_engine.available_languages())
        for name, code in OCR_LANGS.items():
            label = name if code in installed else f"⚠ {name} (paket kurulu değil)"
            combo.addItem(label, code)
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _paint_color_btn(self):
        self.btn_color.setText(self._color)
        self.btn_color.setStyleSheet(
            f"background: {self._color}; color: black; min-width: 80px;"
        )

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Yazı rengi seç")
        if c.isValid():
            self._color = c.name()
            self._paint_color_btn()

    def result_cfg(self) -> dict:
        cfg = self.cfg.copy()
        cfg["target_lang"] = self.cmb_target.currentData()
        cfg["ocr_lang"] = self.cmb_ocr.currentData()
        seq = self.key_edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        hotkey = seq.split(",")[0].strip().lower().replace("meta", "windows")
        if hotkey:
            cfg["hotkey"] = hotkey
        cfg["font_size"] = self.spin_font.value()
        cfg["text_color"] = self._color
        cfg["bg_opacity"] = self.sld_opacity.value() / 100.0
        return cfg
