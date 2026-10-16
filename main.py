"""T — Ekran Çeviri Aracı. Giriş noktası: sistem tepsisi + tüm modüllerin bağlanması."""
import io
import subprocess
import sys
import threading
from pathlib import Path

from PIL import Image
from PySide6.QtCore import (
    Qt, QBuffer, QIODevice, QObject, QRect, QRunnable, QThreadPool, QTimer, Signal,
)
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

import config
import crash_reporter
import ocr_engine
import shortcut
import translator
from floating_logo import FloatingLogo
from hotkey import HotkeyManager
from result_card import ResultCard
from settings_dialog import SettingsDialog
from snip_overlay import SnipOverlay

def _resource_dir() -> Path:
    """Gömülü dosyaların (logo vb.) bulunduğu klasör.

    .exe olarak derlendiğinde PyInstaller içerikleri geçici bir klasöre açar ve
    yolunu sys._MEIPASS'e yazar; kaynak koddan çalışırken normal proje klasörü.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


APP_DIR = _resource_dir()
ICON_PATH = APP_DIR / "assets" / "icon.png"


def load_icon() -> QIcon:
    if ICON_PATH.exists():
        return QIcon(str(ICON_PATH))
    # Logo dosyası yoksa aynı tipografik T işaretini çiz.
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#c0fa45"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, 64, 64, 4, 4)
    p.setPen(QColor("#10251d"))
    p.setFont(QFont("Georgia", 36))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "T")
    p.end()
    return QIcon(pm)


class WorkerSignals(QObject):
    done = Signal(str, str)   # (orijinal, çeviri)
    error = Signal(str)
    status = Signal(str)
    recognized = Signal(str)


class OcrTranslateWorker(QRunnable):
    """OCR + çeviri arka plan iş parçacığında çalışır, arayüz donmaz."""

    def __init__(self, png_bytes: bytes, ocr_lang: str, target_lang: str, original: str = "", provider: str = "mymemory"):
        super().__init__()
        self.png_bytes = png_bytes
        self.ocr_lang = ocr_lang
        self.target_lang = target_lang
        self.signals = WorkerSignals()
        self.original = original
        self.provider = provider
        self.cancelled = threading.Event()

    def run(self):
        try:
            if self.cancelled.is_set():
                return
            original = self.original
            if not original:
                self.signals.status.emit("Ekrandaki metin okunuyor…")
                img = Image.open(io.BytesIO(self.png_bytes)).convert("RGB")
                original = ocr_engine.recognize(img, self.ocr_lang)
            if self.cancelled.is_set():
                return
            if not original:
                self.signals.done.emit("", "")
                return
            self.signals.recognized.emit(original)
            self.signals.status.emit("Metin çevriliyor…")
            translated = translator.translate(original, self.target_lang, cancel_event=self.cancelled,
                                              provider=self.provider, source=self.ocr_lang)
            if not self.cancelled.is_set():
                self.signals.done.emit(original, translated)
        except Exception as e:
            crash_reporter.log_exception("OCR veya çeviri başarısız")
            if not self.cancelled.is_set():
                self.signals.error.emit(str(e))


class TApp(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.cfg = config.load()
        self.icon = load_icon()
        self.pool = QThreadPool.globalInstance()
        self.card: ResultCard | None = None
        self._request_id = 0
        self._snip_pending = False
        self._worker = None
        self._last_capture = None
        self._last_original = ""

        # Ekran seçimi
        self.overlay = SnipOverlay()
        self.overlay.region_selected.connect(self.on_region)
        self.overlay.cancelled.connect(self.restore_logo)
        self.overlay.failed.connect(self.on_capture_error)

        # Yüzen logo
        self.logo = FloatingLogo(self.icon.pixmap(96, 96))
        if self.cfg.get("logo_pos"):
            self.logo.move(*self.cfg["logo_pos"])
        self.logo.clicked.connect(self.trigger_snip)
        self.logo.moved.connect(self.save_logo_pos)
        if self.cfg["show_floating_logo"]:
            self.logo.show()

        # Global kısayol
        self.hotkeys = HotkeyManager()
        self.hotkeys.triggered.connect(self.trigger_snip)
        hotkey_ready = self.hotkeys.register(self.cfg["hotkey"])

        # Sistem tepsisi
        self.tray = QSystemTrayIcon(self.icon)
        self.menu = QMenu()
        act_snip = self.menu.addAction("🖼  Çeviri Yap")
        act_snip.triggered.connect(self.trigger_snip)
        self.act_logo = self.menu.addAction("Yüzen logoyu göster")
        self.act_logo.setCheckable(True)
        self.act_logo.setChecked(self.cfg["show_floating_logo"])
        self.act_logo.toggled.connect(self.set_logo_visible)
        self.menu.addSeparator()
        act_settings = self.menu.addAction("⚙  Ayarlar…")
        act_settings.triggered.connect(self.open_settings)
        act_shortcut = self.menu.addAction("🖥  Masaüstü kısayolu oluştur")
        act_shortcut.triggered.connect(self.create_shortcut)
        act_diag = self.menu.addAction("🩺  Tanılama (sorun mu var?)")
        act_diag.triggered.connect(self.run_diagnostics)
        self.menu.addSeparator()
        act_quit = self.menu.addAction("Çıkış")
        act_quit.triggered.connect(self.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_activated)
        self._update_tooltip()
        self.tray.show()
        if not hotkey_ready:
            QTimer.singleShot(1000, self._notify_hotkey_failure)

    def _notify_hotkey_failure(self):
        self.tray.showMessage(
            "T — Kısayol etkin değil",
            f"{self.cfg['hotkey']} kaydedilemedi. Yüzen logo veya tepsi menüsüyle "
            "çeviri yapabilirsiniz; başka bir kısayolu Ayarlar'dan seçin.",
            self.icon,
        )

    # --- akış ---

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # sol tık
            self.trigger_snip()

    def trigger_snip(self):
        if self._snip_pending or self.overlay.isVisible():
            return
        self._snip_pending = True
        self._request_id += 1
        if getattr(self, "_worker", None) is not None:
            self._worker.cancelled.set()
        # Kart ve logo ekran görüntüsüne girmesin
        if self.card is not None:
            self.card.close()
            self.card = None
        self.logo.hide()
        QTimer.singleShot(180, self._start_overlay)

    def _start_overlay(self):
        self._snip_pending = False
        try:
            self.overlay.start()
        except Exception:
            crash_reporter.log_exception("Ekran yakalama başlatılırken hata")
            self.on_capture_error("Ekran seçimi başlatılamadı. Ayrıntı çökme günlüğüne yazıldı.")

    def restore_logo(self):
        self._snip_pending = False
        if self.cfg["show_floating_logo"]:
            self.logo.show()

    def on_capture_error(self, message: str):
        self.restore_logo()
        self.tray.showMessage("T — Ekran yakalama hatası", message, self.icon)

    def on_region(self, pixmap: QPixmap, rect: QRect):
        self.restore_logo()
        # Önceki OCR/çeviri işi hâlâ sürüyorsa sonucunun bu yeni karta
        # yazılmasını engellemek için her seçime benzersiz bir kimlik ver.
        self._request_id += 1
        request_id = self._request_id
        buf = QBuffer()
        if (
            pixmap.isNull()
            or not buf.open(QIODevice.OpenModeFlag.WriteOnly)
            or not pixmap.save(buf, "PNG")
        ):
            self.on_capture_error("Seçilen alan görüntü dosyasına dönüştürülemedi.")
            return

        self.card = ResultCard(self.cfg)
        self.card.show_for_rect(rect)
        self.card.set_loading()

        self._last_capture = bytes(buf.data())
        self._last_original = ""
        self.card.retry_requested.connect(self.retry_translation)
        self.card.new_selection_requested.connect(self.trigger_snip)
        self.card.settings_requested.connect(self.open_settings)
        self._submit_worker(request_id)

    def _submit_worker(self, request_id: int):
        worker = OcrTranslateWorker(
            self._last_capture, self.cfg["ocr_lang"], self.cfg["target_lang"],
            self._last_original,
            provider=self.cfg.get("provider", "mymemory"),
        )
        self._worker = worker
        worker.signals.done.connect(
            lambda original, translated, rid=request_id: self.on_done(
                rid, original, translated
            )
        )
        worker.signals.error.connect(
            lambda msg, rid=request_id: self.on_error(rid, msg)
        )
        worker.signals.status.connect(
            lambda msg, rid=request_id: self.on_status(rid, msg)
        )
        worker.signals.recognized.connect(
            lambda text, rid=request_id: self.on_recognized(rid, text)
        )
        self.pool.start(worker)

    def retry_translation(self):
        if self.card is None or self._last_capture is None:
            return
        if self._worker is not None:
            self._worker.cancelled.set()
        self._request_id += 1
        self.card.set_loading()
        self._submit_worker(self._request_id)

    def on_status(self, request_id: int, message: str):
        if request_id == self._request_id and self.card is not None:
            self.card.set_status(message)

    def on_recognized(self, request_id: int, original: str):
        if request_id == self._request_id:
            self._last_original = original

    def on_done(self, request_id: int, original: str, translated: str):
        if request_id == self._request_id and self.card is not None:
            self.card.set_result(original, translated)

    def on_error(self, request_id: int, msg: str):
        if request_id == self._request_id and self.card is not None:
            self.card.set_error(msg, getattr(self, "_last_original", ""))

    # --- ayarlar / durum ---

    def set_logo_visible(self, visible: bool):
        self.cfg["show_floating_logo"] = visible
        config.save(self.cfg)
        self.logo.setVisible(visible)

    def save_logo_pos(self, pos):
        self.cfg["logo_pos"] = [pos.x(), pos.y()]
        config.save(self.cfg)

    def open_settings(self):
        dlg = SettingsDialog(self.cfg.copy())
        if dlg.exec():
            self.cfg = dlg.result_cfg()
            config.save(self.cfg)
            if not self.hotkeys.register(self.cfg["hotkey"]):
                self._notify_hotkey_failure()
            self._update_tooltip()
            if self.card is not None and self._last_capture is not None:
                geometry = self.card.geometry()
                self.card.close()
                self.card = ResultCard(self.cfg)
                self.card.setGeometry(geometry)
                self.card.retry_requested.connect(self.retry_translation)
                self.card.new_selection_requested.connect(self.trigger_snip)
                self.card.settings_requested.connect(self.open_settings)
                self.card.show()
                self.retry_translation()

    def _update_tooltip(self):
        self.tray.setToolTip(f"T — Ekran Çevirisi  ({self.cfg['hotkey']})")

    def create_shortcut(self):
        try:
            shortcut.create_desktop_shortcut()
            self.tray.showMessage(
                "T — Ekran Çevirisi", "Masaüstü kısayolu oluşturuldu ✓", self.icon
            )
        except Exception as e:
            QMessageBox.warning(None, "T", f"Kısayol oluşturulamadı:\n{e}")

    def run_diagnostics(self):
        """Tanılamayı ayrı bir süreçte çalıştırır — arayüz kilitlenmesin."""
        try:
            subprocess.Popen(
                [sys.executable] + ([] if getattr(sys, "frozen", False) else [str(APP_DIR / "main.py")])
                + ["--selftest"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as e:
            QMessageBox.warning(None, "T", f"Tanılama başlatılamadı:\n{e}")

    def maybe_offer_shortcut(self):
        """İlk açılışta bir kez sorulur — büyük uygulamaların kurulum adımı gibi."""
        if self.cfg.get("shortcut_asked"):
            return
        self.cfg["shortcut_asked"] = True
        config.save(self.cfg)
        ans = QMessageBox.question(
            None,
            "T — Kurulum",
            "T'ye hoş geldin! 🎉\n\n"
            "Masaüstüne bir kısayol oluşturulsun mu?\n"
            "Böylece uygulamayı tek tıkla başlatabilirsin.\n\n"
            "(İstediğin zaman tepsi menüsünden de oluşturabilirsin.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.create_shortcut()

    def quit(self):
        if self._worker is not None:
            self._worker.cancelled.set()
        self.hotkeys.unregister()
        self.tray.hide()
        self.app.quit()


def selftest() -> int:
    """`T.exe --selftest` ile çalışır: OCR ve çeviri hattını uçtan uca dener.

    Derlenmiş .exe'de konsol olmadığı için sonuç bir rapor dosyasına yazılır ve
    Not Defteri'nde açılır. Bir şey çalışmadığında nedenini görmenin en hızlı
    yolu budur — özellikle OCR dil paketi eksikliğini anında gösterir.
    """
    import tempfile
    from PIL import Image, ImageDraw, ImageFont

    lines = []

    def log(s=""):
        lines.append(s)

    log("T — Tanılama Raporu")
    log("=" * 46)
    log(f"Çalışma biçimi : {'derlenmiş .exe' if getattr(sys, 'frozen', False) else 'kaynak kod'}")
    log(f"Program yolu   : {sys.executable}")
    log(f"Kaynak klasörü : {APP_DIR}")
    log(f"Logo bulundu   : {ICON_PATH.exists()}")
    log()

    ok = True
    cfg = config.load()
    log(f"Ayarlar        : OCR={cfg['ocr_lang']}  hedef={cfg['target_lang']}  kısayol={cfg['hotkey']}")
    log()

    try:
        installed = ocr_engine.available_languages()
        log(f"Kurulu OCR dilleri : {', '.join(installed) if installed else 'HİÇBİRİ'}")
        used = ocr_engine.resolve_language(cfg["ocr_lang"])
        log(f"'{cfg['ocr_lang']}' için kullanılacak motor : {used or 'YOK — dil paketi kurulmalı'}")
        if not installed:
            ok = False
    except Exception as e:
        ok = False
        log(f"OCR dil listesi alınamadı: {e}")
    log()

    # Test görüntüsü üret ve hattı çalıştır
    img = Image.new("RGB", (720, 70), (18, 18, 24))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("segoeui.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    probe = "The ancient door creaks open slowly."
    d.text((18, 18), probe, fill=(235, 235, 240), font=font)

    original = ""
    try:
        original = ocr_engine.recognize(img, cfg["ocr_lang"])
        log(f"OCR beklenen : {probe}")
        log(f"OCR okunan   : {original or '(boş)'}")
        log(f"OCR sonucu   : {'BAŞARILI' if original else 'BAŞARISIZ — metin okunamadı'}")
        if not original:
            ok = False
    except Exception as e:
        ok = False
        log(f"OCR HATASI   : {e}")
    log()

    try:
        translated = translator.translate(original or probe, cfg["target_lang"],
                                          provider=cfg.get("provider", "mymemory"), source=cfg["ocr_lang"])
        log(f"Çeviri       : {translated or '(boş)'}")
        log(f"Çeviri sonucu: {'BAŞARILI' if translated else 'BAŞARISIZ'}")
        if not translated:
            ok = False
    except Exception as e:
        ok = False
        log(f"ÇEVİRİ HATASI: {e}  (internet bağlantısını kontrol et)")
    log()

    log("=" * 46)
    log("GENEL SONUÇ: " + ("HER ŞEY ÇALIŞIYOR" if ok else "SORUN VAR — yukarıya bak"))

    report = "\n".join(lines)
    path = Path(tempfile.gettempdir()) / "T_tanilama.txt"
    path.write_text(report, encoding="utf-8")

    # Konsoldan çalıştırıldıysa ekrana bas; konsol yoksa (tepsi menüsü, .exe)
    # raporu Not Defteri'nde aç. pythonw altında sys.stdout None olabilir.
    has_console = bool(getattr(sys.stdout, "isatty", None) and sys.stdout.isatty())
    if has_console:
        print(report)
    else:
        subprocess.Popen(["notepad.exe", str(path)])
    return 0 if ok else 1


def main():
    crash_reporter.install()
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    app = QApplication(sys.argv)
    app.setApplicationName("T")
    app.setQuitOnLastWindowClosed(False)  # pencereler kapansa da tepside yaşamaya devam
    app.setWindowIcon(load_icon())
    t = TApp(app)  # noqa: F841 — referans tutulmalı
    if "--settings" in sys.argv:
        QTimer.singleShot(100, t.open_settings)
    QTimer.singleShot(600, t.maybe_offer_shortcut)  # tepsi yerleştikten sonra sor
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
