"""Beklenmeyen Python ve yerel süreç çökmelerini kalıcı dosyaya kaydeder."""
import faulthandler
import sys
import threading
import traceback
from datetime import datetime

import config

CRASH_LOG = config.CONFIG_DIR / "crash.log"
_stream = None


def _write_header(stream, context: str) -> None:
    stream.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] {context}\n")


def log_exception(context: str) -> None:
    """Aktif istisnayı günlüğe ekle; günlük yazılamazsa uygulamayı düşürme."""
    try:
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with CRASH_LOG.open("a", encoding="utf-8") as stream:
            _write_header(stream, context)
            traceback.print_exc(file=stream)
    except Exception:
        pass


def install() -> None:
    """Ana ve yardımcı thread istisnalarıyla yerel çökmeler için kancaları kur."""
    global _stream
    try:
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _stream = CRASH_LOG.open("a", encoding="utf-8", buffering=1)
        _write_header(_stream, "Uygulama başlatıldı")
        faulthandler.enable(_stream, all_threads=True)
    except Exception:
        _stream = None

    def handle_exception(exc_type, exc_value, exc_tb):
        try:
            if _stream is not None:
                _write_header(_stream, "Yakalanmamış ana thread hatası")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=_stream)
        finally:
            if sys.stderr is not None:
                sys.__excepthook__(exc_type, exc_value, exc_tb)

    def handle_thread_exception(args):
        try:
            if _stream is not None:
                _write_header(_stream, f"Yakalanmamış thread hatası: {args.thread.name}")
                traceback.print_exception(
                    args.exc_type, args.exc_value, args.exc_traceback, file=_stream
                )
        finally:
            if sys.stderr is not None and hasattr(threading, "__excepthook__"):
                threading.__excepthook__(args)

    sys.excepthook = handle_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = handle_thread_exception
