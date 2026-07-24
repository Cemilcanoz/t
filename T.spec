# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller yapılandırması — tek dosyalık T.exe üretir.

Buradaki asıl iş `excludes` listesi. PySide6 kurulumu ~250 MB'tır çünkü içinde
tarayıcı motoru (QtWebEngine), 3B motor (Qt3D), grafik/multimedya modülleri gibi
bizim hiç kullanmadığımız devasa parçalar var. Bunları dışarıda bırakınca .exe
birkaç yüz MB yerine makul bir boyuta iniyor.

Kullandığımız Qt modülleri sadece: QtCore, QtGui, QtWidgets, QtSvg.

Derlemek için:  venv\\Scripts\\pyinstaller.exe T.spec --noconfirm
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # Logo dosyaları .exe'nin içine gömülür; main.py bunları _MEIPASS'ten okur.
    datas=[
        ('assets/icon.png', 'assets'),
        ('assets/icon.ico', 'assets'),
    ],
    # Dinamik yüklenen (import satırında görünmeyen) modüller
    hiddenimports=[
        'winrt.windows.media.ocr',
        'winrt.windows.globalization',
        'winrt.windows.graphics.imaging',
        'winrt.windows.storage.streams',
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Kullanmadığımız ağır Qt modülleri
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineQuick', 'PySide6.QtWebChannel', 'PySide6.QtWebSockets',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
        'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQuickWidgets',
        'PySide6.QtQml', 'PySide6.QtQuickControls2',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtDesigner',
        'PySide6.QtHelp', 'PySide6.QtPrintSupport', 'PySide6.QtPdf',
        'PySide6.QtPdfWidgets', 'PySide6.QtBluetooth', 'PySide6.QtNfc',
        'PySide6.QtPositioning', 'PySide6.QtSerialPort', 'PySide6.QtSensors',
        'PySide6.QtSpatialAudio', 'PySide6.QtTextToSpeech',
        'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtStateMachine',
        'PySide6.QtUiTools', 'PySide6.QtConcurrent', 'PySide6.QtHttpServer',
        # Bilimsel/geliştirme paketleri (ortamda varsa sızmasın)
        'tkinter', 'numpy', 'scipy', 'pandas', 'matplotlib',
        'PyQt5', 'PyQt6', 'IPython', 'jupyter', 'pytest', 'setuptools',
        'fastapi', 'uvicorn', 'starlette',  # winocr'ın isteğe bağlı sunucu modu
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='T',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX sıkıştırması antivirüs yanlış alarmlarını artırır
    runtime_tmpdir=None,
    console=False,          # konsol penceresi açılmasın
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
