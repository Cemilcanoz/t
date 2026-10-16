"""Konsolsuz dağıtımda kısayol hatasının uygulamayı kapatmaması."""
import unittest
from unittest.mock import patch

from hotkey import HotkeyManager


class HotkeyTests(unittest.TestCase):
    @patch("hotkey.crash_reporter.log_exception")
    @patch("hotkey.keyboard.add_hotkey", side_effect=RuntimeError("erişim reddedildi"))
    def test_registration_failure_without_console(self, add_hotkey, log_exception):
        manager = HotkeyManager()
        with patch("sys.stdout", None):
            self.assertFalse(manager.register("alt+t"))

        self.assertEqual(manager.last_error, "erişim reddedildi")
        log_exception.assert_called_once()
        add_hotkey.assert_called_once()


if __name__ == "__main__":
    unittest.main()
