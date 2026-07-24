"""Global kısayol tuşu — 'keyboard' kütüphanesi kendi thread'inde dinler,
Qt sinyali üzerinden güvenli şekilde ana thread'e iletilir."""
import keyboard
from PySide6.QtCore import QObject, Signal


class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self):
        super().__init__()
        self._handle = None

    def register(self, combo: str) -> bool:
        """Örn: 'alt+t', 'ctrl+shift+t'. Başarılıysa True döner."""
        self.unregister()
        try:
            self._handle = keyboard.add_hotkey(combo, self.triggered.emit)
            return True
        except Exception as e:
            print(f"Kısayol kaydedilemedi ({combo}): {e}")
            return False

    def unregister(self):
        if self._handle is not None:
            try:
                keyboard.remove_hotkey(self._handle)
            except Exception:
                pass
            self._handle = None