"""Masaüstüne kısayol (.lnk) oluşturma — büyük uygulamaların kurulumda yaptığı gibi.

İki farklı çalışma biçimini de desteklemesi gerekiyor:

  * Kaynak koddan  → kısayol pythonw.exe'yi hedefler, argüman olarak main.py verir,
                     ikonu assets/icon.ico dosyasından alır.
  * .exe olarak    → kısayol doğrudan T.exe'yi hedefler, argüman yok. İkon da
                     T.exe'nin içine gömülü olduğu için onu gösterir; assets
                     klasörü geçici bir klasöre açıldığından oraya işaret etmek
                     yanlış olurdu (uygulama kapanınca o klasör silinir).
"""
import subprocess
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
# Kaynak koddan çalışırken proje klasörü; .exe iken exe'nin bulunduğu klasör
APP_DIR = (
    Path(sys.executable).resolve().parent if FROZEN
    else Path(__file__).resolve().parent
)
SHORTCUT_NAME = "T Ekran Çeviri.lnk"


def _ensure_ico() -> Path:
    """Windows kısayolları .ico ister; logo.png'den bir kez üretilir."""
    ico = APP_DIR / "assets" / "icon.ico"
    png = APP_DIR / "assets" / "icon.png"
    if not ico.exists() and png.exists():
        try:
            from PIL import Image
            Image.open(png).save(
                ico,
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
            )
        except Exception:
            pass
    return ico


def create_desktop_shortcut() -> Path:
    if FROZEN:
        target = Path(sys.executable)      # T.exe'nin kendisi
        arguments = ""
        icon_source = target               # ikon exe'ye gömülü
    else:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        target = pythonw if pythonw.exists() else Path(sys.executable)
        arguments = f'"{APP_DIR / "main.py"}"'
        ico = _ensure_ico()
        icon_source = ico if ico.exists() else target

    ps = f"""
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("$desktop\\{SHORTCUT_NAME}")
$s.TargetPath = "{target}"
$s.Arguments = '{arguments}'
$s.WorkingDirectory = "{APP_DIR}"
$s.IconLocation = "{icon_source},0"
$s.Description = "T - Ekran Ceviri Araci"
$s.Save()
Write-Output "$desktop\\{SHORTCUT_NAME}"
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=True,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return Path(result.stdout.strip())
