"""Global kısayol tuşu — 'keyboard' kütüphanesi kendi thread'inde dinler,
Qt sinyali üzerinden güvenli şekilde ana thread'e iletilir."""
import keyboard
from PySide6.QtCore import QObject, Signal

import crash_reporter


class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self):
        super().__init__()
        self._handle = None
        self.last_error = ""

    def register(self, combo: str) -> bool:
        """Örn: 'alt+t', 'ctrl+shift+t'. Başarılıysa True döner."""
        self.unregister()
        self.last_error = ""
        try:
            # Tuş basılı tutulduğunda tarayıcının key-repeat olayları aynı ekran
            # seçimini peş peşe başlatmasın; bırakma anında yalnızca bir kez çalış.
            self._handle = keyboard.add_hotkey(
                combo, self.triggered.emit, trigger_on_release=True
            )
            return True
        except Exception as e:
            self.last_error = str(e)
            crash_reporter.log_exception(f"Kısayol kaydedilemedi: {combo}")
            return False

    def unregister(self):
        if self._handle is not None:
            try:
                keyboard.remove_hotkey(self._handle)
            except Exception:
                pass
            self._handle = None
