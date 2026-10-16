"""T preferences with clear groups and a live reading preview."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QKeySequenceEdit, QLabel, QPushButton, QScrollArea, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)

import ocr_engine
import theme

TARGET_LANGS = {
    "Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr",
    "İspanyolca": "es", "İtalyanca": "it", "Rusça": "ru", "Japonca": "ja",
    "Korece": "ko", "Çince (Basit)": "zh-CN", "Arapça": "ar", "Portekizce": "pt",
}
OCR_LANGS = {
    "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", "Fransızca": "fr",
    "İspanyolca": "es", "İtalyanca": "it", "Rusça": "ru", "Japonca": "ja",
    "Korece": "ko", "Çince (Basit)": "zh-Hans",
}


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("T — Ayarlar")
        self.setMinimumWidth(570)
        self.cfg = cfg
        self._color = cfg["text_color"]
        self.setStyleSheet(theme.CONTROLS + """
            QDialog { background: #10251d; }
            QFrame#section { background: #193329; border: 1px solid #46634b; border-radius: 4px; }
            QLabel#heading { font-size: 14px; font-weight: 600; color: #c0fa45; }
            QLabel#pageTitle { font-size: 23px; font-weight: 600; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)
        root.addWidget(theme.Masthead())
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: #10251d; }")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(14)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        language_card, language_layout = self._section("01  /  Diller ve bağlantı")
        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.cmb_provider = QComboBox()
        self._fill(self.cmb_provider, {"MyMemory · ücretsiz": "mymemory", "Google · ücretsiz": "google"}, cfg.get("provider", "mymemory"))
        form.addRow("Çeviri servisi", self.cmb_provider)
        self.cmb_target = QComboBox()
        self._fill(self.cmb_target, TARGET_LANGS, cfg["target_lang"])
        form.addRow("Çevirinin dili", self.cmb_target)
        self.cmb_ocr = QComboBox()
        self._fill_ocr(self.cmb_ocr, cfg["ocr_lang"])
        form.addRow("Ekrandaki metnin dili", self.cmb_ocr)
        language_layout.addLayout(form)
        self.provider_note = QLabel()
        self.provider_note.setObjectName("muted")
        self.provider_note.setWordWrap(True)
        language_layout.addWidget(self.provider_note)
        self.cmb_provider.currentIndexChanged.connect(self._update_provider_note)
        self._update_provider_note()
        installed = ocr_engine.available_languages()
        names = {code: name for name, code in OCR_LANGS.items()}
        note = QLabel(
            "Kurulu metin tanıma dilleri: " + (", ".join(names.get(x, x) for x in installed) or "yok")
            + ".\nDil paketi yoksa aynı alfabeden kurulu bir dil kullanılır. "
            "Yeni paket: Windows Ayarları › Zaman ve dil › Dil ve bölge."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        language_layout.addWidget(note)
        content_layout.addWidget(language_card)

        shortcut_card, shortcut_layout = self._section("02  /  Tek hareketle")
        shortcut_row = QHBoxLayout()
        shortcut_row.addWidget(QLabel("Ekran seçimi kısayolu"), 1)
        self.key_edit = QKeySequenceEdit(QKeySequence(cfg["hotkey"]))
        self.key_edit.setMinimumWidth(210)
        shortcut_row.addWidget(self.key_edit)
        shortcut_layout.addLayout(shortcut_row)
        hint = QLabel("Kısayola bas, çevirmek istediğin alanı seç.")
        hint.setObjectName("muted")
        shortcut_layout.addWidget(hint)
        content_layout.addWidget(shortcut_card)

        appearance_card, appearance_layout = self._section("03  /  Okuma alanı")
        controls = QHBoxLayout()
        controls.setSpacing(14)
        controls.addWidget(QLabel("Yazı boyutu"))
        self.spin_font = QSpinBox()
        self.spin_font.setRange(8, 40)
        self.spin_font.setSuffix(" pt")
        self.spin_font.setValue(int(cfg["font_size"]))
        controls.addWidget(self.spin_font)
        controls.addStretch()
        controls.addWidget(QLabel("Yazı rengi"))
        self.btn_color = QPushButton()
        self.btn_color.setMinimumWidth(110)
        self.btn_color.clicked.connect(self._pick_color)
        self._paint_color_btn()
        controls.addWidget(self.btn_color)
        appearance_layout.addLayout(controls)
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Arka plan opaklığı"))
        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(20, 100)
        self.sld_opacity.setValue(int(float(cfg["bg_opacity"]) * 100))
        opacity_row.addWidget(self.sld_opacity, 1)
        self.opacity_value = QLabel()
        self.opacity_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.opacity_value.setMinimumWidth(43)
        opacity_row.addWidget(self.opacity_value)
        appearance_layout.addLayout(opacity_row)
        preview_backdrop = QFrame()
        preview_backdrop.setStyleSheet("background: #d8dec7; border-radius: 9px;")
        preview_layout = QVBoxLayout(preview_backdrop)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview = QLabel("Merhaba, dünya.\nÇevirin tam burada.")
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(85)
        self.preview.setMaximumHeight(112)
        preview_layout.addWidget(self.preview)
        appearance_layout.addWidget(preview_backdrop)
        self.spin_font.valueChanged.connect(self._update_preview)
        self.sld_opacity.valueChanged.connect(self._update_preview)
        self._update_preview()
        content_layout.addWidget(appearance_card)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Kaydet")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Vazgeç")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        available = self.screen().availableGeometry()
        self.resize(620, min(760, max(400, available.height() - 70)))

    @staticmethod
    def _section(title):
        card = QFrame()
        card.setObjectName("section")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 13, 16, 14)
        layout.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("heading")
        layout.addWidget(heading)
        return card, layout

    @staticmethod
    def _fill(combo: QComboBox, langs: dict, current: str):
        for name, code in langs.items():
            combo.addItem(name, code)
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    @staticmethod
    def _fill_ocr(combo: QComboBox, current: str):
        """Kurulu olmayan dilleri açıklayıcı bir etiketle göster."""
        current = ocr_engine.LANGUAGE_ALIASES.get(current, current)
        installed = set(ocr_engine.available_languages())
        for name, code in OCR_LANGS.items():
            label = name if code in installed else f"{name} (paket kurulu değil)"
            combo.addItem(label, code)
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _paint_color_btn(self):
        color = QColor(self._color)
        ink = "#10251d" if color.lightness() > 145 else "#ffffff"
        self.btn_color.setText(self._color.upper())
        self.btn_color.setStyleSheet(f"background: {self._color}; color: {ink}; border: 1px solid #64748b;")
        if hasattr(self, "preview"):
            self._update_preview()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Yazı rengi seç")
        if c.isValid():
            self._color = c.name()
            self._paint_color_btn()

    def _update_preview(self):
        self.opacity_value.setText(f"%{self.sld_opacity.value()}")
        self.preview.setText("Merhaba, dünya." if self.spin_font.value() > 24 else "Merhaba, dünya.\nÇevirin tam burada.")
        self.preview.setStyleSheet(
            f"background: rgba(16,37,29,{int(self.sld_opacity.value()*2.55)}); "
            f"color: {self._color}; font-size: {self.spin_font.value()}pt; "
            "border: 1px solid #56705b; border-radius: 9px; padding: 13px;"
        )

    def _update_provider_note(self):
        self.provider_note.setText(
            "MyMemory: günlük 5.000 karakter. Kaynak dili doğru seç. Yalnız okunan metin bu servise gönderilir; ekran görüntüsü bilgisayarında kalır."
            if self.cmb_provider.currentData() == "mymemory" else
            "Google kaynak dili otomatik algılar. Ücretsiz servis bazen istekleri engelleyebilir. Yalnız okunan metin Google’a gönderilir."
        )

    def result_cfg(self) -> dict:
        cfg = self.cfg.copy()
        cfg["provider"] = self.cmb_provider.currentData()
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
