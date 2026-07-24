"""Ayar yönetimi — %APPDATA%/TTranslator/config.json içinde saklanır."""
import json
import os
from pathlib import Path

DEFAULTS = {
    "target_lang": "tr",        # hedef dil (çeviri)
    "ocr_lang": "en",           # ekrandan okunacak metnin dili
    "hotkey": "alt+t",          # global kısayol
    "font_size": 14,
    "text_color": "#FFFFFF",
    "bg_opacity": 0.88,         # kart arka plan opaklığı (0-1)
    "show_floating_logo": True,
    "logo_pos": None,           # [x, y] — yüzen logonun son konumu
    "shortcut_asked": False,    # ilk açılışta "masaüstüne kısayol?" soruldu mu
}

CONFIG_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "TTranslator"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load() -> dict:
    cfg = DEFAULTS.copy()
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return cfg


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )